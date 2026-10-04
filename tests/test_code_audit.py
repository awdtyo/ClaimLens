"""Code audit layer tests: blinding, audit stub, pipeline threading, code API."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from claimlens import sandbox as sandbox_mod
from claimlens.api.app import create_app
from claimlens.api.runs import _enumerate_code
from claimlens.claims.schema import Claim, CodeFinding, Plan, PlanItem
from claimlens.config import ClaimLensConfig
from claimlens.pipeline import make_run_context, run_stage
from claimlens.verify import code_audit as audit_mod

PDF_BYTES = b"%PDF-1.4\n%test\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


@pytest.fixture()
def isolated_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Run context with isolated LLM cache and fake provider."""
    monkeypatch.setenv("CLAIMLENS_PROVIDER", "fake")
    monkeypatch.setenv("CLAIMLENS_NO_SLEEP", "1")
    monkeypatch.setenv("CLAIMLENS_CACHE_DIR", str(tmp_path / "llm_cache"))
    return make_run_context("audit-test", runs_root=tmp_path / "runs")


@pytest.fixture()
def mock_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """Test client running the mock pipeline with zero delay."""
    monkeypatch.setenv("CLAIMLENS_MOCK_PIPELINE", "1")
    monkeypatch.setenv("CLAIMLENS_MOCK_DELAY", "0")
    monkeypatch.setenv("CLAIMLENS_NO_SLEEP", "1")
    config = ClaimLensConfig.from_env()
    assert config.mock_pipeline is True
    app = create_app(runs_root=tmp_path / "runs", config=config)
    with TestClient(app) as test_client:
        yield test_client


def _leaky_plan() -> Plan:
    """Plan whose steps leak reported values, simulating a worst case."""
    return Plan(
        items=[
            PlanItem(
                claim_id="c1",
                steps=["Reproduce 0.912 accuracy (reported 91.2%) in 10 epochs"],
                scale_factor=0.1,
                scale_reason="Cheap.",
                config={"epochs": 10, "note": "target 91.2"},
            )
        ],
        assumptions=[
            {
                "id": "a1",
                "detail": "seed",
                "value_chosen": "0",
                "reason": "stated",
                "confidence": "high",
            }
        ],
    )


def _claims() -> list[Claim]:
    return [Claim(id="c1", text="Method X reaches 91.2%.", source_ref="t1", reported_value=0.912)]


def test_blinded_removes_reported_values() -> None:
    blinded = _leaky_plan().blinded(_claims())
    dumped = json.dumps(blinded.model_dump(mode="json"))
    assert "0.912" not in dumped
    assert "91.2" not in dumped
    assert "[redacted]" in dumped


def test_blinded_preserves_hyperparameters_and_original() -> None:
    plan = _leaky_plan()
    blinded = plan.blinded(_claims())
    assert blinded.items[0].config["epochs"] == 10
    assert blinded.assumptions[0].value_chosen == "0"
    assert blinded is not plan
    assert "0.912" in plan.items[0].steps[0]


def test_blinded_without_claims_returns_plain_copy() -> None:
    plan = _leaky_plan()
    blinded = plan.blinded()
    assert blinded == plan
    assert blinded is not plan


def test_blinded_leaves_integral_counts_in_place() -> None:
    """Documented limit: bare counts collide with ordinary integers."""
    plan = Plan(items=[PlanItem(claim_id="c1", steps=["Finish in 12 minutes"], config={})])
    claims = [Claim(id="c1", text="12 minutes.", source_ref="t1", reported_value=12.0)]
    assert "12 minutes" in plan.blinded(claims).items[0].steps[0]


def test_sandbox_receives_only_blinded_plan(
    isolated_run,
    monkeypatch: pytest.MonkeyPatch,  # type: ignore[no-untyped-def]
) -> None:
    """Pipeline integration: no reported value may reach an agent prompt."""
    received: dict = {}
    recorded: list[str] = []

    def fake_run_experiments(plan: Plan, run):  # type: ignore[no-untyped-def]
        received["plan"] = plan
        prompt = "\n".join(step for item in plan.items for step in item.steps) + json.dumps(
            [item.config for item in plan.items]
        )
        run.llm.complete(  # type: ignore[union-attr]
            task="agent_task",
            messages=[{"role": "user", "content": prompt}],
            role="agent",
        )
        return []

    def spy_complete(task, messages, schema=None, tools=None, role="agent"):  # type: ignore[no-untyped-def]
        recorded.extend(
            str(message.get("content", ""))
            for message in messages
            if isinstance(message.get("content"), str)
        )
        return {}

    monkeypatch.setattr(sandbox_mod, "run_experiments", fake_run_experiments)
    monkeypatch.setattr(isolated_run.llm, "complete", spy_complete)
    run_stage("sandbox", isolated_run, {"plan": _leaky_plan(), "claims": _claims()})

    assert recorded, "the fake agent must actually send a prompt"
    for text in [json.dumps(received["plan"].model_dump(mode="json")), *recorded]:
        assert "0.912" not in text
        assert "91.2" not in text


def test_audit_code_stub_raises(isolated_run) -> None:  # type: ignore[no-untyped-def]
    plan = Plan()
    with pytest.raises(NotImplementedError):
        audit_mod.audit_code([], [], plan, isolated_run)


def test_code_audit_stage_calls_stub(isolated_run) -> None:  # type: ignore[no-untyped-def]
    plan = Plan()
    with pytest.raises(NotImplementedError):
        run_stage("code_audit", isolated_run, {"claims": [], "plan": plan, "evidence": []})


def test_sample_code_findings_validate(fixtures_dir: Path) -> None:
    data = json.loads((fixtures_dir / "sample_code_findings.json").read_text(encoding="utf-8"))
    findings = [CodeFinding.model_validate(item) for item in data]
    blocking = [item for item in findings if item.severity == "blocking"]
    warnings = [item for item in findings if item.severity == "warning"]
    assert len(blocking) == 1 and not blocking[0].advisory
    assert len(warnings) == 1 and warnings[0].advisory
    for finding in findings:
        assert (fixtures_dir / finding.file).exists(), f"missing fixture file {finding.file}"


def test_mock_code_findings_validate(fixtures_dir: Path) -> None:
    data = json.loads((fixtures_dir / "mock_code_findings.json").read_text(encoding="utf-8"))
    findings = [CodeFinding.model_validate(item) for item in data]
    assert any(item.severity == "blocking" and not item.advisory for item in findings)
    assert any(item.severity == "warning" and item.advisory for item in findings)


def test_enumerate_code_empty_dir(tmp_path: Path) -> None:
    assert _enumerate_code(tmp_path / "missing") == []


def _wait_for_done(client: TestClient, run_id: str, timeout: float = 20.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        detail = client.get(f"/api/runs/{run_id}").json()
        if detail["status"] in ("done", "failed", "cancelled"):
            return detail
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not finish in {timeout}s")


def test_mock_run_includes_code_audit_stage(mock_client: TestClient) -> None:
    resp = mock_client.post(
        "/api/runs", files={"file": ("paper.pdf", PDF_BYTES, "application/pdf")}
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]
    detail = _wait_for_done(mock_client, run_id)
    assert detail["status"] == "done"
    assert detail["stages"]["code_audit"]["status"] == "done"
    findings = mock_client.get(f"/api/runs/{run_id}/verdicts").json()
    assert any(v.get("code_findings") for v in findings)


def test_code_tree_and_file_content(mock_client: TestClient, fixtures_dir: Path) -> None:
    resp = mock_client.post(
        "/api/runs", files={"file": ("paper.pdf", PDF_BYTES, "application/pdf")}
    )
    assert resp.status_code == 202
    run_id = resp.json()["run_id"]
    _wait_for_done(mock_client, run_id)

    tree = mock_client.get(f"/api/runs/{run_id}/code").json()
    assert tree["run_id"] == run_id
    c1 = next(entry for entry in tree["claims"] if entry["claim_id"] == "c1")
    assert [iteration["iteration"] for iteration in c1["iterations"]] == [1, 2]
    first = c1["iterations"][0]["files"][0]
    assert first["name"] == "train.py"

    content = mock_client.get(f"/api/runs/{run_id}/code/c1/1/{first['index']}")
    assert content.status_code == 200
    expected = (fixtures_dir / "code" / "c1" / "iter_1" / "train.py").read_bytes()
    assert content.content == expected


def test_code_file_unknown_paths_404(mock_client: TestClient) -> None:
    resp = mock_client.post(
        "/api/runs", files={"file": ("paper.pdf", PDF_BYTES, "application/pdf")}
    )
    run_id = resp.json()["run_id"]
    _wait_for_done(mock_client, run_id)
    assert mock_client.get(f"/api/runs/{run_id}/code/nope/1/0").status_code == 404
    assert mock_client.get(f"/api/runs/{run_id}/code/c1/9/0").status_code == 404
    assert mock_client.get(f"/api/runs/{run_id}/code/c1/1/9").status_code == 404
    assert mock_client.get(f"/api/runs/{'0' * 32}/code").status_code == 404
