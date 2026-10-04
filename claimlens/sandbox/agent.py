"""Agent loop with function calling (Stage 5).

One loop per plan item with a hard iteration cap. The agent can only
return measured values, which become :class:`Evidence`; it can never
mark a claim done. Failed or capped runs return ``Evidence`` with
``measured_value=None`` and a failure note in ``method`` — never an
invented number.

Every iteration's code is snapshotted to
``runs/<run_id>/code/<claim_id>/iter_<n>/`` *before* it runs, and every
step is reported via ``run.emit("sandbox", "progress", ...)`` with short
messages that never carry API keys or full file contents.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from claimlens.claims.schema import Evidence, PlanItem
from claimlens.config import RunContext
from claimlens.sandbox import docker_runner
from claimlens.sandbox.tools import TOOL_DEFINITIONS, SandboxTools

MAX_ITERATIONS = 8
MEASURED_RE = re.compile(r"MEASURED\s+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)")
SUMMARY_CHARS = 200

SYSTEM_PROMPT = (
    "You reproduce one paper claim with a small sandbox experiment. "
    "Write code with write_file, run it with run_in_sandbox, read results with read_file. "
    "Needed PyPI packages go through install_package. "
    "When a run prints the final number, reply with JSON "
    '{"measured_value": <number>, "method": "<one line>"} and stop. '
    "Print the result inside the sandbox as 'MEASURED <number>'. "
    "Never invent a number: if the code fails, say why instead."
)


def _short(text: str, limit: int = SUMMARY_CHARS) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit] + "..."


def _tool_summary(name: str, args: Any) -> str:
    """One-line tool summary without file contents or secrets."""
    items = args if isinstance(args, dict) else {}
    if name == "write_file":
        content = str(items.get("content", ""))
        return f"write_file path={items.get('path')!r} bytes={len(content.encode())}"
    if name == "run_in_sandbox":
        return f"run_in_sandbox command={items.get('command')!r}"
    if name == "install_package":
        return f"install_package package={items.get('package')!r}"
    if name == "read_file":
        return f"read_file path={items.get('path')!r}"
    return f"{name} {_short(json.dumps(args, default=str))}"


def _extract_tool_calls(response: Any) -> list[dict[str, Any]]:
    """Accept OpenAI-style tool_calls and simple {action, ...} responses."""
    if not isinstance(response, dict):
        return []
    calls = response.get("tool_calls")
    if isinstance(calls, list):
        normalized = []
        for call in calls:
            fn = call.get("function", {}) if isinstance(call, dict) else {}
            normalized.append(
                {
                    "name": fn.get("name", call.get("name", "")),
                    "arguments": fn.get("arguments", call.get("arguments", {})),
                }
            )
        return [call for call in normalized if call["name"]]
    action = response.get("action")
    if isinstance(action, str):
        args = {key: value for key, value in response.items() if key != "action"}
        return [{"name": action, "arguments": args}]
    return []


def _extract_measured(response: Any) -> float | None:
    if not isinstance(response, dict):
        return None
    value = response.get("measured_value")
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _snapshot(workdir: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for path in sorted(workdir.rglob("*")):
        if not path.is_file():
            continue
        target = dest / path.relative_to(workdir)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)


def run_agent_for_claim(
    claim_id: str,
    item: PlanItem,
    run: RunContext,
    llm: Any | None = None,
    run_fn: Any | None = None,
    max_iterations: int = MAX_ITERATIONS,
) -> Evidence:
    """Run the tool loop for one plan item and return its Evidence.

    Args:
        claim_id: Claim under reproduction.
        item: Blinded plan item (steps, scale factor, config).
        run: Per-run context (code snapshots and logs land in run_dir).
        llm: Model gateway; defaults to ``run.llm``. Tests inject a
            scripted stub with the same ``complete(...)`` signature.
        run_fn: Optional ``(command, timeout_s, packages) -> DockerResult``
            override so tests run without Docker. Defaults to Docker.
        max_iterations: Hard cap on model turns.
    """
    gateway = llm if llm is not None else run.llm
    if gateway is None:
        raise ValueError("The sandbox agent needs an LLM gateway.")
    run_dir = Path(run.run_dir)  # type: ignore[arg-type]
    code_root = run_dir / "code" / claim_id
    tmp = tempfile.TemporaryDirectory(prefix=f"claimlens-{claim_id}-")
    workdir = Path(tmp.name)
    tools = SandboxTools(workdir, run_fn=run_fn)
    iterations = 0
    last_stdout = ""
    last_exit: int | None = None

    prompt_lines = [
        f"Claim {claim_id}: reproduce it at scale_factor={item.scale_factor}.",
        *[f"Step {n}: {step}" for n, step in enumerate(item.steps, 1)],
        f"Config: {json.dumps(item.config, sort_keys=True)}",
    ]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(prompt_lines)},
    ]
    run.emit("sandbox", "progress", f"{claim_id}: agent started", {"claim_id": claim_id})

    def fail_evidence(reason: str) -> Evidence:
        evidence_id = f"e_{claim_id}"
        logs_ref = _write_log(run_dir, evidence_id, last_stdout, reason)
        return Evidence(
            id=evidence_id,
            claim_id=claim_id,
            method=f"agent failed: {reason}",
            measured_value=None,
            config=dict(item.config),
            logs_ref=logs_ref,
            scale_factor=item.scale_factor,
            code_dir=f"code/{claim_id}",
            iterations=iterations,
        )

    try:
        for _ in range(max_iterations):
            try:
                response = gateway.complete(
                    task=f"sandbox_{claim_id}",
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    role="agent",
                )
            except Exception as e:  # noqa: BLE001 - model errors end this claim's loop.
                run.emit("sandbox", "progress", f"{claim_id}: llm error", {"claim_id": claim_id})
                return fail_evidence(f"llm error: {_short(e)}")

            calls = _extract_tool_calls(response)
            measured = _extract_measured(response)
            if measured is not None and not calls:
                evidence_id = f"e_{claim_id}"
                logs_ref = _write_log(run_dir, evidence_id, last_stdout, "")
                run.emit(
                    "sandbox",
                    "progress",
                    f"{claim_id}: measured {measured}",
                    {"claim_id": claim_id, "measured_value": measured},
                )
                return Evidence(
                    id=evidence_id,
                    claim_id=claim_id,
                    method=f"docker: agent experiment for {claim_id} at scale {item.scale_factor}",
                    measured_value=measured,
                    config=dict(item.config),
                    logs_ref=logs_ref,
                    scale_factor=item.scale_factor,
                    code_dir=f"code/{claim_id}",
                    iterations=iterations,
                )
            if not calls:
                hint = _short(response.get("text", json.dumps(response, default=str)))
                messages.append(
                    {"role": "user", "content": f"No tool call understood ({hint}). Use a tool."}
                )
                run.emit(
                    "sandbox", "progress", f"{claim_id}: unparseable reply", {"claim_id": claim_id}
                )
                continue

            for call in calls:
                name = str(call["name"])
                args = call["arguments"]
                run.emit(
                    "sandbox",
                    "progress",
                    f"{claim_id}: {_tool_summary(name, args)}",
                    {"claim_id": claim_id, "tool": name},
                )
                if name == "run_in_sandbox":
                    iterations += 1
                    _snapshot(workdir, code_root / f"iter_{iterations}")
                try:
                    outcome = tools.dispatch(name, args)
                except Exception as e:  # noqa: BLE001 - tool errors are observations, not crashes.
                    outcome = {"ok": False, "error": _short(e)}
                if name == "run_in_sandbox":
                    last_exit = int(outcome.get("exit_code", -1))
                    last_stdout = str(outcome.get("stdout", ""))
                    observed = MEASURED_RE.findall(last_stdout)
                    note = f" Observed MEASURED {observed[-1]}." if observed else ""
                    run.emit(
                        "sandbox",
                        "progress",
                        f"{claim_id}: exit {last_exit}{note}",
                        {"claim_id": claim_id, "exit_code": last_exit},
                    )
                else:
                    run.emit(
                        "sandbox",
                        "progress",
                        f"{claim_id}: {name} {'ok' if outcome.get('ok') else 'failed'}",
                        {"claim_id": claim_id, "tool": name},
                    )
                shown = {
                    key: value
                    for key, value in outcome.items()
                    if key in ("ok", "error", "exit_code", "timed_out", "path", "package")
                }
                if outcome.get("stdout") or outcome.get("stderr"):
                    shown["stdout_tail"] = _short(outcome.get("stdout", ""))
                    shown["stderr_tail"] = _short(outcome.get("stderr", ""))
                messages.append(
                    {
                        "role": "user",
                        "content": f"Tool {name} result: {json.dumps(shown, default=str)}",
                    }
                )

        run.emit(
            "sandbox", "progress", f"{claim_id}: iteration cap reached", {"claim_id": claim_id}
        )
        return fail_evidence(f"iteration cap ({max_iterations}) reached without a measured value")
    finally:
        tmp.cleanup()


def _write_log(run_dir: Path, evidence_id: str, stdout: str, note: str) -> str:
    name = f"04_sandbox_{evidence_id}.log"
    body = stdout[-docker_runner.MAX_OUTPUT_BYTES :]
    if note:
        body = f"{body}\n[claimlens] {note}".strip()
    (run_dir / name).write_text(body, encoding="utf-8")
    return name


def run_agent() -> None:
    """Run the experiment agent loop until a measured value is produced."""
    raise NotImplementedError
