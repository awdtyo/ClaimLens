"""Sandbox tools exposed to the experiment agent (Stage 5).

The model reaches the sandbox only through these tools, issued as
function calls: ``run_in_sandbox``, ``read_file``, ``write_file``,
``install_package`` and ``report_result``. File tools operate inside
one claim workdir on the host; execution itself always goes through
:mod:`claimlens.sandbox.docker_runner`, never the host.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from claimlens.sandbox import docker_runner

MAX_READ_CHARS = 4000
MAX_RESULT_CHARS = 4000
PACKAGE_RE = re.compile(r"^[A-Za-z0-9_.-]+(\[[A-Za-z0-9_,.-]+\])?(==[A-Za-z0-9_.-]+)?$")

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "write_file",
        "description": "Write experiment code or data to a path in the claim workdir.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path, e.g. train.py."},
                "content": {"type": "string", "description": "File content."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a file from the claim workdir (truncated past 4000 chars).",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "run_in_sandbox",
        "description": (
            "Run a command in the Docker sandbox with no network access. "
            "Packages recorded via install_package are installed first. "
            "Stdout may carry a line 'MEASURED <number>' with the result."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command argv, e.g. ['python', 'train.py'].",
                },
                "timeout_s": {"type": "integer", "description": "Wall-clock limit."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "install_package",
        "description": "Record a PyPI package to pip-install before the next sandbox run.",
        "parameters": {
            "type": "object",
            "properties": {"package": {"type": "string", "description": "E.g. numpy==1.26.4."}},
            "required": ["package"],
        },
    },
    {
        "name": "report_result",
        "description": (
            "Finish the experiment: report the final measured number from a "
            "sandbox run. Call once, after run_in_sandbox printed it."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "measured_value": {"type": "number"},
                "method": {"type": "string"},
            },
            "required": ["measured_value"],
        },
    },
]


def list_tools() -> list[dict[str, Any]]:
    """Return the tool definitions available to the agent."""
    return [dict(tool) for tool in TOOL_DEFINITIONS]


def _safe_rel(path: str) -> Path:
    rel = Path(path)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(f"Refusing path outside the workdir: {path!r}.")
    return rel


class SandboxTools:
    """Stateful tool backend for one claim: a workdir plus package list."""

    def __init__(
        self,
        workdir: Path | str,
        run_fn: Any | None = None,
        default_timeout_s: int = docker_runner.DEFAULT_TIMEOUT_S,
    ) -> None:
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.packages: list[str] = []
        self.default_timeout_s = default_timeout_s
        self._run_fn = run_fn

    # -- file tools ----------------------------------------------------

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        try:
            dest = self.workdir / _safe_rel(path)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return {"ok": True, "path": str(_safe_rel(path)), "bytes": len(content.encode())}

    def read_file(self, path: str) -> dict[str, Any]:
        try:
            dest = self.workdir / _safe_rel(path)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        if not dest.is_file():
            return {"ok": False, "error": f"No such file: {path!r}."}
        text = dest.read_text(encoding="utf-8", errors="replace")
        truncated = len(text) > MAX_READ_CHARS
        return {"ok": True, "path": path, "content": text[:MAX_READ_CHARS], "truncated": truncated}

    # -- execution tools -------------------------------------------------

    def install_package(self, package: str) -> dict[str, Any]:
        name = package.strip()
        if not PACKAGE_RE.match(name):
            return {"ok": False, "error": f"Refusing package spec: {package!r}."}
        if name not in self.packages:
            self.packages.append(name)
        return {"ok": True, "package": name, "pending": list(self.packages)}

    def report_result(self, measured_value: Any, method: str = "") -> dict[str, Any]:
        """Record the agent's final measurement (validated, never invented here)."""
        try:
            number = float(measured_value)
        except (TypeError, ValueError):
            return {
                "ok": False,
                "error": f"measured_value must be a number, got {measured_value!r}.",
            }
        if not math.isfinite(number):
            return {"ok": False, "error": "measured_value must be finite."}
        return {"ok": True, "measured_value": number, "method": method}

    def run_in_sandbox(self, command: list[str], timeout_s: int | None = None) -> dict[str, Any]:
        if not command or not all(isinstance(part, str) for part in command):
            return {"ok": False, "error": "command must be a non-empty list of strings."}
        limit = timeout_s or self.default_timeout_s
        packages = list(self.packages)
        self.packages.clear()
        if self._run_fn is not None:
            result = self._run_fn(command, timeout_s=limit, packages=packages)
        else:
            result = docker_runner.run_in_docker(
                command,
                packages=packages or None,
                timeout_s=limit,
                workdir=self.workdir,
            )
        stdout = result.stdout[-MAX_RESULT_CHARS:]
        stderr = result.stderr[-MAX_RESULT_CHARS:]
        return {
            "ok": result.exit_code == 0 and not result.timed_out,
            "exit_code": result.exit_code,
            "timed_out": result.timed_out,
            "stdout": stdout,
            "stderr": stderr,
        }

    # -- dispatch ----------------------------------------------------------

    def dispatch(self, name: str, arguments: dict[str, Any] | str) -> dict[str, Any]:
        """Execute one model-issued tool call by name."""
        args = json.loads(arguments) if isinstance(arguments, str) else dict(arguments or {})
        if name == "write_file":
            return self.write_file(str(args.get("path", "")), str(args.get("content", "")))
        if name == "read_file":
            return self.read_file(str(args.get("path", "")))
        if name == "run_in_sandbox":
            command = args.get("command", [])
            timeout = args.get("timeout_s")
            return self.run_in_sandbox(
                [str(part) for part in command],
                timeout_s=int(timeout) if timeout is not None else None,
            )
        if name == "install_package":
            return self.install_package(str(args.get("package", "")))
        if name == "report_result":
            return self.report_result(args.get("measured_value"), str(args.get("method", "")))
        return {"ok": False, "error": f"Unknown tool: {name!r}."}
