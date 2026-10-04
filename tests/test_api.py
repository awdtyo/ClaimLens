"""API tests in mock mode (no API key, no Docker, no network)."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from claimlens.api import runs as runs_mod
from claimlens.api.app import create_app
from claimlens.config import ClaimLensConfig

PDF_BYTES = b"%PDF-1.4\n%test\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"
UUID_RE = re.compile(r"^[0-9a-f]{32}$")


@pytest.fixture()
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAIMLENS_MOCK_PIPELINE", "1")
    monkeypatch.setenv("CLAIMLENS_MOCK_DELAY", "0")
    monkeypatch.setenv("CLAIMLENS_NO_SLEEP", "1")


@pytest.fixture()
def client(mock_env: None, tmp_path: Path):  # type: ignore[no-untyped-def]
    config = ClaimLensConfig.from_env()
    assert config.mock_pipeline is True
    app = create_app(runs_root=tmp_path / "runs", config=config)
    with TestClient(app) as test_client:
        yield test_client


def upload_pdf(client: TestClient, payload: bytes = PDF_BYTES) -> str:
    resp = client.post("/api/runs", files={"file": ("paper.pdf", payload, "application/pdf")})
    assert resp.status_code == 202, resp.text
    run_id = resp.json()["run_id"]
    assert UUID_RE.fullmatch(run_id)
    return run_id


def wait_for_done(client: TestClient, run_id: str, timeout: float = 20.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        detail = client.get(f"/api/runs/{run_id}").json()
        if detail["status"] in ("done", "failed", "cancelled"):
            return detail
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not finish in {timeout}s")


def test_health(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_config_exposes_no_keys(client: TestClient) -> None:
    resp = client.get("/api/config")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"provider", "model_planner", "model_agent", "model_fast"}
    assert "key" not in json.dumps(body).lower()


def test_upload_rejects_wrong_content_type(client: TestClient) -> None:
    resp = client.post("/api/runs", files={"file": ("paper.txt", b"hello", "text/plain")})
    assert resp.status_code == 415


def test_upload_rejects_bad_magic(client: TestClient) -> None:
    resp = client.post("/api/runs", files={"file": ("paper.pdf", b"not a pdf", "application/pdf")})
    assert resp.status_code == 400


def test_upload_rejects_oversize(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runs_mod, "MAX_UPLOAD_BYTES", 10)
    resp = client.post(
        "/api/runs",
        files={"file": ("paper.pdf", PDF_BYTES, "application/pdf")},
    )
    assert resp.status_code == 413


def test_mock_run_completes_and_artifacts_fetch(client: TestClient) -> None:
    run_id = upload_pdf(client)
    detail = wait_for_done(client, run_id)
    assert detail["status"] == "done"
    assert detail["demo"] is False
    assert {s["status"] for s in detail["stages"].values()} == {"done"}
    for stage in detail["stages"].values():
        assert stage["started_at"] and stage["ended_at"]

    parsed = client.get(f"/api/runs/{run_id}/parsed").json()
    assert len(parsed["table_mismatches"]) == 1

    claims = client.get(f"/api/runs/{run_id}/claims").json()
    assert all("page" in c for c in claims)

    verdicts = client.get(f"/api/runs/{run_id}/verdicts").json()
    assert {v["status"] for v in verdicts} == {
        "replicated",
        "partially replicated",
        "not replicated",
        "untestable",
    }
    not_replicated = next(v for v in verdicts if v["status"] == "not replicated")
    assert len(not_replicated["assumption_effects"]) == 2

    plan = client.get(f"/api/runs/{run_id}/plan").json()
    assert plan["items"]
    evidence = client.get(f"/api/runs/{run_id}/evidence").json()
    assert evidence

    report = client.get(f"/api/runs/{run_id}/report")
    assert report.status_code == 200
    assert "replicated" in report.text

    paper = client.get(f"/api/runs/{run_id}/paper")
    assert paper.status_code == 200
    assert paper.content.startswith(b"%PDF")


def test_sse_streams_events_to_completion(client: TestClient) -> None:
    run_id = upload_pdf(client)
    stages: set[str] = set()
    agent_lines = 0
    terminal = None
    deadline = time.time() + 20.0
    with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        assert resp.status_code == 200
        for line in resp.iter_lines():
            assert time.time() < deadline, "SSE stream did not finish in time"
            if not line or not line.startswith("data:"):
                continue
            event = json.loads(line[len("data:") :])
            stages.add(event["stage"])
            if event["stage"] == "sandbox" and "agent:" in (event["message"] or ""):
                agent_lines += 1
            if event["stage"] == "run" and event["status"] in ("done", "failed"):
                terminal = event
                break
    assert terminal is not None and terminal["status"] == "done"
    assert {"ingest", "claims", "plan", "sandbox", "verify", "report", "run"} <= stages
    assert agent_lines >= 3


def test_cancel_stops_run(mock_env: None, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAIMLENS_MOCK_DELAY", "0.5")
    config = ClaimLensConfig.from_env()
    app = create_app(runs_root=tmp_path / "runs", config=config)
    with TestClient(app) as test_client:
        run_id = upload_pdf(test_client)
        resp = test_client.post(f"/api/runs/{run_id}/cancel")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"
        detail = test_client.get(f"/api/runs/{run_id}").json()
        assert detail["status"] == "cancelled"


def test_demo_filter(client: TestClient) -> None:
    demos = client.get("/api/runs", params={"demo": True}).json()
    assert len(demos) == 2
    assert all(d["demo"] is True for d in demos)
    run_id = upload_pdf(client)
    wait_for_done(client, run_id)
    non_demos = client.get("/api/runs", params={"demo": False}).json()
    assert all(d["demo"] is False for d in non_demos)
    assert any(d["run_id"] == run_id for d in non_demos)
    everything = client.get("/api/runs").json()
    assert len(everything) >= 3


def test_unknown_run_and_artifact_404(client: TestClient) -> None:
    missing = "0" * 32
    assert client.get(f"/api/runs/{missing}").status_code == 404
    assert client.get(f"/api/runs/{missing}/events").status_code == 404
    assert client.post(f"/api/runs/{missing}/cancel").status_code == 404
    run_id = upload_pdf(client)
    wait_for_done(client, run_id)
    assert client.get(f"/api/runs/{run_id}/nope").status_code == 404
    assert client.get(f"/api/runs/{run_id}/../state").status_code in (404, 422)
    assert client.get("/api/runs/not-a-uuid").status_code == 404
