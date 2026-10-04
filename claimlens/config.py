"""Runtime configuration for ClaimLens, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


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
        )

    def model_for_role(self, role: str) -> str:
        """Return the configured model name for a role."""
        if role == "planner":
            return self.model_planner
        if role == "fast":
            return self.model_fast
        return self.model_agent


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
