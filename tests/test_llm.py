"""Fake LLM provider returns valid JSON without an API key."""

from __future__ import annotations

import json
from pathlib import Path

from claimlens.config import ClaimLensConfig
from claimlens.llm import LLMGateway, chunk_text


def test_fake_llm_returns_valid_json(fake_config: ClaimLensConfig, tmp_path: Path) -> None:
    gateway = LLMGateway(config=fake_config, run_dir=tmp_path / "runs" / "smoke")
    result = gateway.complete(
        task="smoke_test",
        messages=[{"role": "user", "content": "Return status."}],
        role="fast",
    )
    assert isinstance(result, (dict, list))
    json.dumps(result)
    assert result["status"] == "ok"


def test_fake_llm_logs_tokens(fake_config: ClaimLensConfig, tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "smoke"
    gateway = LLMGateway(config=fake_config, run_dir=run_dir)
    gateway.complete(
        task="smoke_test",
        messages=[{"role": "user", "content": "Return status."}],
        role="fast",
    )
    log_path = run_dir / "llm_log.jsonl"
    assert log_path.exists()
    entry = json.loads(log_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert entry["task"] == "smoke_test"
    assert entry["prompt_tokens"] >= 1


def test_chunk_text_respects_budget() -> None:
    text = "para one\n\npara two\n\npara three"
    chunks = chunk_text(text, max_tokens=4)
    assert len(chunks) >= 1
    assert "".join(chunks).replace("\n", "") == text.replace("\n", "")


def test_fixtures_dir_has_fake_responses(fixtures_dir: Path) -> None:
    assert (fixtures_dir / "fake_llm_responses.json").exists()
