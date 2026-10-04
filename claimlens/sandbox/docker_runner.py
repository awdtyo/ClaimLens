"""Docker runner: execute generated experiment code in a sandbox.

Production path for every experiment: code runs inside Docker, never on
the host (AGENTS.md hard rule 7). Each run has two phases:

1. Install phase (network enabled): ``pip install`` the requested
   packages so experiment code can import them.
2. Run phase (network disabled): the experiment command runs with CPU,
   memory and wall-clock limits and no network access.

Tests that need a Docker daemon are marked ``docker`` and skipped when
Docker is absent.
"""

from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_IMAGE = "python:3.11-slim"
DEFAULT_TIMEOUT_S = 300
DEFAULT_INSTALL_TIMEOUT_S = 300
DEFAULT_CPUS = 1.0
DEFAULT_MEM = "512m"
WORKDIR = "/work"
MAX_OUTPUT_BYTES = 1_000_000


@dataclass
class DockerResult:
    """Outcome of one sandboxed command."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    output_files: dict[str, bytes] = field(default_factory=dict)


def _client() -> Any:
    """Return a docker client, or raise a clear error when unusable."""
    try:
        import docker
    except ImportError as e:
        raise RuntimeError("The 'docker' package is required to run the sandbox.") from e
    try:
        client = docker.from_env()
        client.ping()
    except Exception as e:
        raise RuntimeError(f"Docker daemon is not reachable: {e}") from e
    return client


def docker_available() -> bool:
    """Return True when a Docker daemon answers."""
    try:
        _client()
    except RuntimeError:
        return False
    return True


def ensure_image(image: str = DEFAULT_IMAGE) -> str:
    """Pull *image* when it is missing locally; return the image name."""
    client = _client()
    try:
        client.images.get(image)
    except Exception:  # noqa: BLE001 - any lookup failure means "pull it".
        logger.debug("Pulling sandbox image %s.", image)
        client.images.pull(image)
    return image


def build_image(dockerfile: str, tag: str, context: Path | str | None = None) -> str:
    """Build an image from a Dockerfile string; return the tag.

    Args:
        dockerfile: Dockerfile contents.
        tag: Tag to apply to the built image.
        context: Build context directory. Defaults to a temp dir holding
            only the Dockerfile.
    """
    client = _client()
    ctx = Path(context) if context is not None else Path(tempfile.mkdtemp(prefix="claimlens-ctx-"))
    ctx.mkdir(parents=True, exist_ok=True)
    (ctx / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    client.images.build(path=str(ctx), tag=tag, rm=True)
    return tag


def _write_files(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        dest = root / rel
        if ".." in Path(rel).parts:
            raise ValueError(f"Refusing path outside the workdir: {rel!r}.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


def _collect_files(root: Path) -> dict[str, bytes]:
    collected: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            try:
                data = path.read_bytes()
            except OSError:
                continue
            collected[str(path.relative_to(root))] = data[:MAX_OUTPUT_BYTES]
    return collected


def _decode(raw: bytes | str | None) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    return raw.decode("utf-8", errors="replace")


def run_in_docker(
    command: list[str] | str,
    files: dict[str, str] | None = None,
    packages: list[str] | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    cpus: float = DEFAULT_CPUS,
    mem: str = DEFAULT_MEM,
    image: str = DEFAULT_IMAGE,
    install_timeout_s: int = DEFAULT_INSTALL_TIMEOUT_S,
    workdir: Path | str | None = None,
) -> DockerResult:
    """Run a command inside Docker and collect stdout plus output files.

    Args:
        command: Command to run in the run phase (network disabled),
            e.g. ``["python", "train.py"]``.
        files: Extra files to place in the container workdir before
            running, as relative path -> text content.
        packages: PyPI packages installed in a prior network-enabled
            install phase (``pip install``). Empty means no install.
        timeout_s: Wall-clock limit for the run phase. A script still
            running afterwards is killed and reported with
            ``timed_out=True``.
        cpus: CPU limit for the run-phase container.
        mem: Memory limit for the run-phase container (e.g. ``"512m"``).
        image: Base image for both phases.
        install_timeout_s: Wall-clock limit for the install phase.
        workdir: Optional host directory to use as the shared workdir.
            Defaults to a fresh temp directory.

    Returns:
        DockerResult with exit code, stdout/stderr, timeout flag and a
        snapshot of the workdir files after the run.
    """
    ensure_image(image)
    tmp: tempfile.TemporaryDirectory[str] | None = None
    if workdir is None:
        tmp = tempfile.TemporaryDirectory(prefix="claimlens-run-")
        root = Path(tmp.name)
    else:
        root = Path(workdir)
        root.mkdir(parents=True, exist_ok=True)
    try:
        _write_files(root, files or {})

        if packages:
            install = run_phase(
                ["pip", "install", *packages],
                root=root,
                image=image,
                timeout_s=install_timeout_s,
                cpus=cpus,
                mem=mem,
                network_disabled=False,
            )
            if install.exit_code != 0 or install.timed_out:
                install.stderr = f"install phase failed: {install.stderr}"
                return install

        return run_phase(
            command,
            root=root,
            image=image,
            timeout_s=timeout_s,
            cpus=cpus,
            mem=mem,
            network_disabled=True,
        )
    finally:
        if tmp is not None:
            tmp.cleanup()


def run_phase(
    command: list[str] | str,
    root: Path | str,
    image: str = DEFAULT_IMAGE,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    cpus: float = DEFAULT_CPUS,
    mem: str = DEFAULT_MEM,
    network_disabled: bool = True,
) -> DockerResult:
    """Run one container phase against a host workdir mounted at /work."""
    client = _client()
    root = Path(root)
    container = client.containers.run(
        image,
        command,
        working_dir=WORKDIR,
        volumes={str(root): {"bind": WORKDIR, "mode": "rw"}},
        network_disabled=network_disabled,
        mem_limit=mem,
        nano_cpus=int(cpus * 1_000_000_000),
        detach=True,
        stdout=True,
        stderr=True,
    )
    timed_out = False
    exit_code = -1
    try:
        try:
            waited = container.wait(timeout=timeout_s)
            if isinstance(waited, dict):
                exit_code = int(waited.get("StatusCode", exit_code))
        except Exception:  # noqa: BLE001 - wait raises transport timeouts; kill below.
            # Any wait failure (including timeout) kills the container;
            # only a still-running container afterwards counts as a timeout.
            timed_out = True
            try:
                container.kill()
            except Exception:  # noqa: BLE001 - container may already be gone.
                logger.debug("Container kill after wait failure was a no-op.")
            try:
                waited = container.wait(timeout=30)
                if isinstance(waited, dict):
                    exit_code = int(waited.get("StatusCode", exit_code))
            except Exception:  # noqa: BLE001 - best effort exit-code recovery.
                logger.debug("Could not recover exit code after kill.")
        # A wait that returned while the container still runs is a timeout.
        try:
            container.reload()
            if container.status in ("running", "restarting", "paused"):
                timed_out = True
                try:
                    container.kill()
                except Exception:  # noqa: BLE001 - container may exit on its own.
                    logger.debug("Container kill after slow run was a no-op.")
                try:
                    waited = container.wait(timeout=30)
                    if isinstance(waited, dict):
                        exit_code = int(waited.get("StatusCode", exit_code))
                except Exception:  # noqa: BLE001 - best effort exit-code recovery.
                    logger.debug("Could not recover exit code after kill.")
        except Exception:  # noqa: BLE001 - reload fails once the container is gone.
            logger.debug("Container reload after wait was a no-op.")
    finally:
        try:
            stdout = _decode(container.logs(stdout=True, stderr=False))
        except Exception:  # noqa: BLE001 - logs may be unavailable post-kill.
            logger.debug("Could not read container stdout.")
            stdout = ""
        try:
            stderr = _decode(container.logs(stdout=False, stderr=True))
        except Exception:  # noqa: BLE001 - logs may be unavailable post-kill.
            logger.debug("Could not read container stderr.")
            stderr = ""
        try:
            container.remove(force=True)
        except Exception:  # noqa: BLE001 - cleanup must not mask the result.
            logger.debug("Container remove was a no-op.")
    if timed_out:
        stderr = f"{stderr}\n[claimlens] container killed after {timeout_s}s time limit.".strip()
    output_files = _collect_files(root)
    # Keep the snapshot bounded for transport.
    total = 0
    trimmed: dict[str, bytes] = {}
    for name in sorted(output_files):
        data = output_files[name]
        if total + len(data) > MAX_OUTPUT_BYTES:
            break
        trimmed[name] = data
        total += len(data)
    return DockerResult(
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        output_files=trimmed,
    )


def container_env_without_secrets(env: dict[str, str] | None = None) -> dict[str, str]:
    """Return env with likely secret values stripped (for logging)."""
    env = dict(os.environ if env is None else env)
    for key in list(env):
        upper = key.upper()
        if "KEY" in upper or "TOKEN" in upper or "SECRET" in upper:
            env[key] = "[redacted]"
    return env
