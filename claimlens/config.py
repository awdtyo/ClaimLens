"""Runtime configuration for ClaimLens, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class ClaimLensConfig:
    """Configuration loaded from environment variables."""

    provider: str = "gemini"
    model_planner: str = "gemma-4-31b-it"
    model_agent: str = "gemma-4-26b-a4b-it"
    model_fast: str = "gemma-4-e4b-it"
    max_context: int = 30000
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    max_concurrent_runs: int = 1
    mock_pipeline: bool = False
    # Failover when the primary provider rate-limits (HTTP 429). Empty
    # disables automatic fallback. The key comes from OPENROUTER_API_KEY.
    fallback_provider: str = "openrouter"
    # Models used whenever the effective provider is OpenRouter. Only
    # these two free Gemma 4 variants are allowed (planner = 31B,
    # agent/fast = 26B-A4B).
    openrouter_model_planner: str = "google/gemma-4-31b-it:free"
    openrouter_model_agent: str = "google/gemma-4-26b-a4b-it:free"
    openrouter_model_fast: str = "google/gemma-4-26b-a4b-it:free"

    #: The only models ClaimLens may use through OpenRouter.
    OPENROUTER_ALLOWED_MODELS: ClassVar[frozenset[str]] = frozenset(
        {
            "google/gemma-4-31b-it:free",
            "google/gemma-4-26b-a4b-it:free",
        }
    )

    @classmethod
    def from_env(cls) -> ClaimLensConfig:
        """Build a config from environment variables with AGENTS.md defaults."""
        return cls(
            provider=os.environ.get("CLAIMLENS_PROVIDER", "gemini"),
            model_planner=os.environ.get("CLAIMLENS_MODEL_PLANNER", "gemma-4-31b-it"),
            model_agent=os.environ.get("CLAIMLENS_MODEL_AGENT", "gemma-4-26b-a4b-it"),
            model_fast=os.environ.get("CLAIMLENS_MODEL_FAST", "gemma-4-e4b-it"),
            max_context=int(os.environ.get("CLAIMLENS_MAX_CONTEXT", "30000")),
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            openrouter_api_key=os.environ.get("OPENROUTER_API_KEY", ""),
            max_concurrent_runs=int(os.environ.get("CLAIMLENS_MAX_CONCURRENT_RUNS", "1")),
            mock_pipeline=os.environ.get("CLAIMLENS_MOCK_PIPELINE", "0") == "1",
            fallback_provider=os.environ.get("CLAIMLENS_FALLBACK_PROVIDER", "openrouter"),
            openrouter_model_planner=os.environ.get(
                "CLAIMLENS_OPENROUTER_MODEL_PLANNER", "google/gemma-4-31b-it:free"
            ),
            openrouter_model_agent=os.environ.get(
                "CLAIMLENS_OPENROUTER_MODEL_AGENT", "google/gemma-4-26b-a4b-it:free"
            ),
            openrouter_model_fast=os.environ.get(
                "CLAIMLENS_OPENROUTER_MODEL_FAST", "google/gemma-4-26b-a4b-it:free"
            ),
        )

    def model_for_role(self, role: str, provider: str | None = None) -> str:
        """Return the configured model name for a role and provider.

        When the effective provider is ``openrouter``, only the two free
        Gemma 4 models are ever returned (planner -> 31B, agent/fast ->
        26B-A4B); a misconfigured non-allowlisted value falls back to
        the role default so quota keys never hit an unexpected model.
        """
        effective = provider or self.provider
        if effective == "openrouter":
            return self.openrouter_model_for_role(role)
        if role == "planner":
            return self.model_planner
        if role == "fast":
            return self.model_fast
        return self.model_agent

    def openrouter_model_for_role(self, role: str) -> str:
        """Return the allowlisted OpenRouter model for a role."""
        if role == "planner":
            candidate = self.openrouter_model_planner
            default = "google/gemma-4-31b-it:free"
        else:
            # Both "agent" and "fast" run on the smaller free variant.
            candidate = (
                self.openrouter_model_agent if role == "agent" else self.openrouter_model_fast
            )
            default = "google/gemma-4-26b-a4b-it:free"
        if candidate not in self.OPENROUTER_ALLOWED_MODELS:
            return default
        return candidate

    def fallback_for(self, primary: str) -> str | None:
        """Return the fallback provider for a primary, or None if disabled."""
        if not self.fallback_provider or self.fallback_provider == primary:
            return None
        if self.fallback_provider != "openrouter":
            return self.fallback_provider
        key = self.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            return None
        return "openrouter"


@dataclass
class RunContext:
    """Per-run context injected into every stage.

    Attributes:
        run_id: Unique id for this run (directory name under runs/).
        run_dir: Directory where stage artifacts and logs are written.
        config: Runtime configuration.
        llm: Model gateway. Typed as object to avoid a circular import;
            at runtime it is a claimlens.llm.LLMGateway.
    """

    run_id: str
    run_dir: object  # pathlib.Path at runtime
    config: ClaimLensConfig = field(default_factory=ClaimLensConfig)
    llm: object | None = None

    def emit(
        self,
        stage: str,
        status: str,
        message: str | None = None,
        data: object = None,
    ) -> dict:
        """Record a run event and notify live subscribers.

        Appends ``{"ts", "run_id", "stage", "status", "message", "data"}``
        to ``runs/<run_id>/events.jsonl``. ``status`` is one of
        ``started``, ``progress``, ``done``, ``failed``.
        """
        from pathlib import Path

        from claimlens.events import append_event

        return append_event(Path(self.run_dir), self.run_id, stage, status, message, data)  # type: ignore[arg-type]
