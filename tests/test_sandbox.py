"""Sandbox tests (Part 2).

Docker tests are marked ``docker`` and skipped when no Docker daemon is
reachable. Everything else runs with injected fakes: generated code is
never executed on the host.
"""

from __future__ import annotations

import pytest

from claimlens.sandbox import docker_runner

pytestmark = pytest.mark.docker


@pytest.fixture()
def image() -> str:
    if not docker_runner.docker_available():
        pytest.skip("Docker daemon is not reachable.")
    try:
        return docker_runner.ensure_image()
    except Exception as e:  # noqa: BLE001 - any pull failure means "skip".
        pytest.skip(f"Could not pull sandbox image: {e}")
    return docker_runner.DEFAULT_IMAGE


def test_hello_world_returns_output(image: str) -> None:
    result = docker_runner.run_in_docker(
        ["python", "-c", "print('hello claimlens')"],
        image=image,
        timeout_s=60,
    )
    assert result.exit_code == 0
    assert not result.timed_out
    assert "hello claimlens" in result.stdout


def test_files_are_copied_in_and_results_out(image: str) -> None:
    result = docker_runner.run_in_docker(
        ["python", "hello.py"],
        files={"hello.py": "print(open('in.txt').read())", "in.txt": "data123"},
        image=image,
        timeout_s=60,
    )
    assert result.exit_code == 0
    assert "data123" in result.stdout
    assert result.output_files["in.txt"].decode() == "data123"


def test_script_writing_output_file_is_collected(image: str) -> None:
    result = docker_runner.run_in_docker(
        ["python", "-c", "open('out.txt','w').write('measured 0.5')"],
        image=image,
        timeout_s=60,
    )
    assert result.exit_code == 0
    assert result.output_files["out.txt"] == b"measured 0.5"


def test_overtime_script_is_killed_and_reported(image: str) -> None:
    result = docker_runner.run_in_docker(
        ["python", "-c", "import time; time.sleep(60)"],
        image=image,
        timeout_s=3,
    )
    assert result.timed_out
    assert "time limit" in result.stderr


def test_run_phase_has_no_network(image: str) -> None:
    probe = (
        "import socket; "
        "socket.create_connection(('8.8.8.8', 53), timeout=3); "
        "print('NETWORK-REACHABLE')"
    )
    result = docker_runner.run_in_docker(
        ["python", "-c", probe],
        image=image,
        timeout_s=60,
    )
    assert "NETWORK-REACHABLE" not in result.stdout
    assert result.exit_code != 0 or result.timed_out


def test_resource_limits_are_accepted(image: str) -> None:
    result = docker_runner.run_in_docker(
        ["python", "-c", "print('limited ok')"],
        image=image,
        timeout_s=60,
        cpus=0.5,
        mem="256m",
    )
    assert result.exit_code == 0
    assert "limited ok" in result.stdout


def test_failing_command_reports_exit_code(image: str) -> None:
    result = docker_runner.run_in_docker(
        ["python", "-c", "raise SystemExit(3)"],
        image=image,
        timeout_s=60,
    )
    assert result.exit_code == 3
    assert not result.timed_out
