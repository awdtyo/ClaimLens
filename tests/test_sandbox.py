"""Sandbox tests (Part 2).

Docker tests are marked ``docker`` and skipped when no Docker daemon is
reachable. Everything else runs with injected fakes: generated code is
never executed on the host.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from claimlens.claims.schema import PlanItem
from claimlens.pipeline import make_run_context
from claimlens.sandbox import agent as agent_mod
from claimlens.sandbox import docker_runner
from claimlens.sandbox.docker_runner import DockerResult
from claimlens.sandbox.tools import SandboxTools, list_tools

needs_docker = pytest.mark.docker


@pytest.fixture()
def image() -> str:
    if not docker_runner.docker_available():
        pytest.skip("Docker daemon is not reachable.")
    try:
        return docker_runner.ensure_image()
    except Exception as e:  # noqa: BLE001 - any pull failure means "skip".
        pytest.skip(f"Could not pull sandbox image: {e}")
    return docker_runner.DEFAULT_IMAGE


@needs_docker
def test_hello_world_returns_output(image: str) -> None:
    result = docker_runner.run_in_docker(
        ["python", "-c", "print('hello claimlens')"],
        image=image,
        timeout_s=60,
    )
    assert result.exit_code == 0
    assert not result.timed_out
    assert "hello claimlens" in result.stdout


@needs_docker
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


@needs_docker
def test_script_writing_output_file_is_collected(image: str) -> None:
    result = docker_runner.run_in_docker(
        ["python", "-c", "open('out.txt','w').write('measured 0.5')"],
        image=image,
        timeout_s=60,
    )
    assert result.exit_code == 0
    assert result.output_files["out.txt"] == b"measured 0.5"


@needs_docker
def test_overtime_script_is_killed_and_reported(image: str) -> None:
    result = docker_runner.run_in_docker(
        ["python", "-c", "import time; time.sleep(60)"],
        image=image,
        timeout_s=3,
    )
    assert result.timed_out
    assert "time limit" in result.stderr


@needs_docker
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


@needs_docker
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


@needs_docker
def test_failing_command_reports_exit_code(image: str) -> None:
    result = docker_runner.run_in_docker(
        ["python", "-c", "raise SystemExit(3)"],
        image=image,
        timeout_s=60,
    )
    assert result.exit_code == 3
    assert not result.timed_out


# -- tools (no Docker) ----------------------------------------------------


def test_tool_definitions_cover_required_tools() -> None:
    assert {tool["name"] for tool in list_tools()} == {
        "run_in_sandbox",
        "read_file",
        "write_file",
        "install_package",
        "report_result",
    }


def test_write_read_roundtrip(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path / "work")
    assert tools.write_file("exp.py", "print(1)")["ok"]
    outcome = tools.read_file("exp.py")
    assert outcome == {"ok": True, "path": "exp.py", "content": "print(1)", "truncated": False}


def test_paths_cannot_escape_workdir(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path / "work")
    assert not tools.write_file("../evil.py", "x")["ok"]
    assert not tools.read_file("/etc/hostname")["ok"]
    assert not tools.read_file("missing.py")["ok"]


def test_install_package_validates_spec(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path / "work")
    assert tools.install_package("numpy==1.26.4")["ok"]
    assert tools.install_package("numpy==1.26.4")["pending"] == ["numpy==1.26.4"]
    assert not tools.install_package("numpy; rm -rf /")["ok"]


def test_report_result_validates_numbers(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path / "work")
    ok = tools.dispatch("report_result", {"measured_value": 0.91, "method": "train X"})
    assert ok == {"ok": True, "measured_value": 0.91, "method": "train X"}
    assert tools.dispatch("report_result", {"measured_value": "lot"})["ok"] is False
    assert tools.dispatch("report_result", {})["ok"] is False


def test_dispatch_accepts_json_string_args(tmp_path: Path) -> None:
    tools = SandboxTools(tmp_path / "work")
    outcome = tools.dispatch("write_file", json.dumps({"path": "a.txt", "content": "hi"}))
    assert outcome["ok"]
    assert tools.dispatch("nope", {})["ok"] is False


def test_run_uses_injected_runner_without_docker(tmp_path: Path) -> None:
    def fake_run(
        command: list[str], timeout_s: int = 60, packages: list[str] | None = None
    ) -> DockerResult:
        assert command == ["python", "exp.py"]
        assert packages == ["numpy==1.26.4"]
        return DockerResult(exit_code=0, stdout="MEASURED 0.5", stderr="", timed_out=False)

    tools = SandboxTools(tmp_path / "work", run_fn=fake_run)
    assert tools.install_package("numpy==1.26.4")["ok"]
    outcome = tools.run_in_sandbox(["python", "exp.py"])
    assert outcome["ok"]
    assert outcome["stdout"] == "MEASURED 0.5"
    # Packages are consumed by the run they were recorded for.
    assert tools.packages == []


# -- agent loop (no Docker) -------------------------------------------------


class ScriptedLLM:
    """Fake gateway replaying queued responses like function-call turns."""

    def __init__(self, script: list[dict[str, Any]]) -> None:
        self.script = list(script)
        self.prompts: list[str] = []

    def complete(
        self,
        task: str,
        messages: list[dict[str, Any]],
        schema: Any | None = None,
        tools: Any | None = None,
        role: str = "agent",
    ) -> Any:
        self.prompts.append("\n".join(str(message.get("content", "")) for message in messages))
        assert task.startswith("sandbox_")
        assert tools, "the agent must offer function-calling tools"
        if self.script:
            return self.script.pop(0)
        return {"text": "no further instructions"}


def _ok_run(
    command: list[str], timeout_s: int = 60, packages: list[str] | None = None
) -> DockerResult:
    assert command[:1] == ["python"]
    return DockerResult(exit_code=0, stdout="MEASURED 0.908\n", stderr="", timed_out=False)


def _failing_run(
    command: list[str], timeout_s: int = 60, packages: list[str] | None = None
) -> DockerResult:
    return DockerResult(exit_code=1, stdout="", stderr="boom", timed_out=False)


def _item() -> PlanItem:
    return PlanItem(
        claim_id="c1",
        steps=["Train method X on a 10% subsample", "Record accuracy"],
        scale_factor=0.1,
        scale_reason="Cheap scaled run.",
        config={"epochs": 10},
    )


def test_agent_never_sees_reported_values_in_any_format(tmp_path: Path) -> None:
    """Blinded generation: the distinctive value 0.9173 reaches no prompt."""
    from claimlens.claims.schema import Claim, Plan

    claim = Claim(
        id="c9",
        text="Method Z reaches 91.73% accuracy.",
        source_ref="t1",
        metric="accuracy",
        reported_value=0.9173,
        tolerance=0.01,
    )
    leaky = Plan(
        items=[
            PlanItem(
                claim_id="c9",
                steps=["Reproduce the reported 0.9173 accuracy (91.73%)", "Record accuracy"],
                scale_factor=0.1,
                scale_reason="Target 91.73% is costly at full scale.",
                config={"epochs": 10, "note": "target 91.73%"},
            )
        ],
        assumptions=[],
    )
    blinded = leaky.blinded([claim])
    run = make_run_context("agent-blind", runs_root=tmp_path / "runs")
    llm = ScriptedLLM(
        [
            {
                "tool_calls": [
                    {
                        "name": "write_file",
                        "arguments": {"path": "exp.py", "content": "print('MEASURED 0.91')"},
                    }
                ]
            },
            {
                "tool_calls": [
                    {"name": "run_in_sandbox", "arguments": {"command": ["python", "exp.py"]}}
                ]
            },
            {"measured_value": 0.91},
        ]
    )
    evidence = agent_mod.run_agent_for_claim("c9", blinded.items[0], run, llm=llm, run_fn=_ok_run)
    assert evidence.measured_value == 0.91
    assert llm.prompts, "the loop must actually prompt the model"
    for prompt in llm.prompts:
        assert "0.9173" not in prompt
        assert "91.73" not in prompt
        assert "91.73%" not in prompt


def test_agent_finishes_through_report_result_tool(tmp_path: Path) -> None:
    """Gemini-style finish: forced function calls end via report_result."""
    run = make_run_context("agent-report-tool", runs_root=tmp_path / "runs")
    llm = ScriptedLLM(
        [
            {
                "tool_calls": [
                    {
                        "name": "write_file",
                        "arguments": {"path": "exp.py", "content": "print('MEASURED 0.77')"},
                    }
                ]
            },
            {
                "tool_calls": [
                    {"name": "run_in_sandbox", "arguments": {"command": ["python", "exp.py"]}}
                ]
            },
            {
                "tool_calls": [
                    {
                        "name": "report_result",
                        "arguments": {"measured_value": 0.77, "method": "train X on 10%"},
                    }
                ]
            },
        ]
    )
    evidence = agent_mod.run_agent_for_claim("c1", _item(), run, llm=llm, run_fn=_ok_run)
    assert evidence.measured_value == 0.77
    assert evidence.iterations == 1
    assert (Path(run.run_dir) / "code" / "c1" / "iter_1" / "exp.py").exists()


def test_writes_are_snapshotted_even_without_a_run(tmp_path: Path) -> None:
    """Capped runs that only wrote files still preserve their code."""
    run = make_run_context("agent-writeonly", runs_root=tmp_path / "runs")
    llm = ScriptedLLM(
        [
            {
                "tool_calls": [
                    {"name": "write_file", "arguments": {"path": "exp.py", "content": "print(1)"}}
                ]
            }
        ]
        * 3
    )
    evidence = agent_mod.run_agent_for_claim(
        "c1", _item(), run, llm=llm, run_fn=_failing_run, max_iterations=2
    )
    assert evidence.measured_value is None
    assert evidence.iterations == 0
    assert (Path(run.run_dir) / "code" / "c1" / "iter_1" / "exp.py").exists()


def test_code_written_events_carry_names_not_contents(tmp_path: Path) -> None:
    run = make_run_context("agent-code-events", runs_root=tmp_path / "runs")
    llm = ScriptedLLM(
        [
            {
                "tool_calls": [
                    {
                        "name": "write_file",
                        "arguments": {"path": "train.py", "content": "SENSITIVE-BLOB print(1)"},
                    }
                ]
            },
            {
                "tool_calls": [
                    {"name": "run_in_sandbox", "arguments": {"command": ["python", "train.py"]}}
                ]
            },
            {"measured_value": 0.5},
        ]
    )
    evidence = agent_mod.run_agent_for_claim("c1", _item(), run, llm=llm, run_fn=_ok_run)
    assert evidence.code_dir == "code/c1"
    assert evidence.iterations == 1
    assert (Path(run.run_dir) / "code" / "c1" / "iter_1" / "train.py").exists()
    events = [
        json.loads(line)
        for line in (Path(run.run_dir) / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    written = [event for event in events if event["stage"] == "code_written"]
    assert len(written) == 1
    event = written[0]
    assert event["status"] == "progress"
    assert event["data"] == {"claim_id": "c1", "iter": 1, "file": "train.py"}
    assert "SENSITIVE-BLOB" not in str(event["message"])
    assert "SENSITIVE-BLOB" not in json.dumps(event["data"])


def test_agent_writes_code_runs_it_and_returns_evidence(tmp_path: Path) -> None:
    run = make_run_context("agent-ok", runs_root=tmp_path / "runs")
    llm = ScriptedLLM(
        [
            {
                "tool_calls": [
                    {
                        "name": "write_file",
                        "arguments": {"path": "exp.py", "content": "print('MEASURED 0.908')"},
                    }
                ]
            },
            {
                "tool_calls": [
                    {"name": "run_in_sandbox", "arguments": {"command": ["python", "exp.py"]}}
                ]
            },
            {"measured_value": 0.908, "method": "train X on 10% subsample"},
        ]
    )
    evidence = agent_mod.run_agent_for_claim("c1", _item(), run, llm=llm, run_fn=_ok_run)
    assert evidence.claim_id == "c1"
    assert evidence.measured_value == 0.908
    assert evidence.scale_factor == 0.1
    assert evidence.iterations == 1
    assert evidence.code_dir == "code/c1"
    assert (Path(run.run_dir) / "code" / "c1" / "iter_1" / "exp.py").exists()
    assert (Path(run.run_dir) / str(evidence.logs_ref)).exists()


def test_agent_emits_progress_without_secrets_or_file_contents(tmp_path: Path) -> None:
    run = make_run_context("agent-events", runs_root=tmp_path / "runs")
    llm = ScriptedLLM(
        [
            {
                "tool_calls": [
                    {
                        "name": "write_file",
                        "arguments": {
                            "path": "exp.py",
                            "content": "SECRET-BLOB print('MEASURED 0.5')",
                        },
                    }
                ]
            },
            {
                "tool_calls": [
                    {"name": "run_in_sandbox", "arguments": {"command": ["python", "exp.py"]}}
                ]
            },
            {"measured_value": 0.5},
        ]
    )
    agent_mod.run_agent_for_claim("c1", _item(), run, llm=llm, run_fn=_ok_run)
    events = [
        json.loads(line)
        for line in (Path(run.run_dir) / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    sandbox_events = [event for event in events if event["stage"] == "sandbox"]
    assert len(sandbox_events) >= 5
    assert all(event["status"] == "progress" for event in sandbox_events)
    assert all(len(str(event["message"] or "")) <= 260 for event in sandbox_events)
    assert all("SECRET-BLOB" not in str(event["message"]) for event in sandbox_events)


def test_iteration_cap_stops_a_looping_agent(tmp_path: Path) -> None:
    run = make_run_context("agent-loop", runs_root=tmp_path / "runs")
    llm = ScriptedLLM(
        [
            {
                "tool_calls": [
                    {"name": "run_in_sandbox", "arguments": {"command": ["python", "exp.py"]}}
                ]
            }
        ]
        * 5
    )
    evidence = agent_mod.run_agent_for_claim(
        "c1", _item(), run, llm=llm, run_fn=_failing_run, max_iterations=2
    )
    assert evidence.measured_value is None
    assert "iteration cap" in evidence.method
    assert evidence.iterations == 2
    assert (Path(run.run_dir) / "code" / "c1" / "iter_2").is_dir()


def test_failed_runs_never_invent_a_value(tmp_path: Path) -> None:
    run = make_run_context("agent-fail", runs_root=tmp_path / "runs")
    llm = ScriptedLLM([{"text": "I give up"}])
    evidence = agent_mod.run_agent_for_claim(
        "c1", _item(), run, llm=llm, run_fn=_failing_run, max_iterations=1
    )
    assert evidence.measured_value is None
    assert evidence.claim_id == "c1"


# -- run_experiments wiring (no Docker) ---------------------------------------


def test_run_experiments_runs_every_item_in_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import claimlens.sandbox as sandbox_mod
    from claimlens.claims.schema import Evidence, Plan

    run = make_run_context("sandbox-wiring", runs_root=tmp_path / "runs")
    plan = Plan(items=[_item(), _item().model_copy(update={"claim_id": "c2"})])
    seen: list[str] = []

    def fake_agent(claim_id: str, item: Any, run: Any) -> Evidence:
        seen.append(claim_id)
        return Evidence(
            id=f"e_{claim_id}",
            claim_id=claim_id,
            method="fake",
            measured_value=0.5,
            scale_factor=item.scale_factor,
        )

    monkeypatch.setattr(sandbox_mod, "run_agent_for_claim", fake_agent)
    evidence = sandbox_mod.run_experiments(plan, run)
    assert [item.claim_id for item in evidence] == ["c1", "c2"]
    assert [item.id for item in evidence] == ["e_c1", "e_c2"]
    assert seen == ["c1", "c2"]
    events = [
        json.loads(line)
        for line in (Path(run.run_dir) / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    stages = [(event["stage"], event["status"]) for event in events if event["stage"] == "sandbox"]
    assert stages[0] == ("sandbox", "started")
    assert stages[-1] == ("sandbox", "done")


def test_run_experiments_empty_plan(tmp_path: Path) -> None:
    import claimlens.sandbox as sandbox_mod
    from claimlens.claims.schema import Plan

    run = make_run_context("sandbox-empty", runs_root=tmp_path / "runs")
    assert sandbox_mod.run_experiments(Plan(), run) == []
