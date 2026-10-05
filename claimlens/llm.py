"""Single model gateway for ClaimLens.

All model calls in the codebase go through this module. No other file
imports a model SDK; providers are reached over HTTP with httpx.

Providers: ``gemini``, ``openrouter``, ``ollama`` and ``fake``.
The ``fake`` provider returns canned JSON from
``tests/fixtures/fake_llm_responses.json`` keyed by ``task``, so tests
run without an API key.

Rate-limit failover: when the primary provider keeps returning HTTP
429, the gateway automatically retries once through
``CLAIMLENS_FALLBACK_PROVIDER`` (default ``openrouter``, needs
``OPENROUTER_API_KEY``). Through OpenRouter only the two free Gemma 4
models are used: planner -> ``google/gemma-4-31b-it:free``,
agent/fast -> ``google/gemma-4-26b-a4b-it:free``.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import httpx

from claimlens.config import ClaimLensConfig

VALID_ROLES = ("planner", "agent", "fast")
RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
BASE_BACKOFF_S = 1.0


class RateLimitError(RuntimeError):
    """Raised when a provider keeps returning HTTP 429 (quota exhausted)."""


def is_rate_limit_error(exc: BaseException) -> bool:
    """Check whether an exception signals rate limiting / quota exhaustion."""
    if isinstance(exc, RateLimitError):
        return True
    text = str(exc).lower()
    return (
        "http 429" in text
        or "429 " in text
        or "rate limit" in text
        or "rate-limit" in text
        or "quota" in text
        or "resource_exhausted" in text
    )


def _approx_tokens(text: str) -> int:
    """Rough token estimate used when a provider reports no usage."""
    return max(1, len(text) // 4)


def approx_tokens(text: str) -> int:
    """Public rough token estimate (characters / 4) for chunking decisions."""
    return _approx_tokens(text)


def _messages_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(str(m.get("content", "")) for m in messages)


def chunk_text(text: str, max_tokens: int) -> list[str]:
    """Split text into chunks under roughly ``max_tokens`` each.

    Splits on paragraph boundaries; a single oversized paragraph is
    hard-split. Token counts are approximated as ``len(chars) // 4``.
    """
    if max_tokens <= 0:
        raise ValueError("max_tokens must be positive.")
    if _approx_tokens(text) <= max_tokens:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for para in text.split("\n\n"):
        para_tokens = _approx_tokens(para)
        if para_tokens > max_tokens:
            # Hard-split oversized paragraph by characters.
            step = max_tokens * 4
            for i in range(0, len(para), step):
                piece = para[i : i + step]
                if current_tokens + _approx_tokens(piece) > max_tokens and current:
                    chunks.append("\n\n".join(current))
                    current, current_tokens = [], 0
                current.append(piece)
                current_tokens += _approx_tokens(piece)
            continue
        if current_tokens + para_tokens > max_tokens and current:
            chunks.append("\n\n".join(current))
            current, current_tokens = [], 0
        current.append(para)
        current_tokens += para_tokens
    if current:
        chunks.append("\n\n".join(current))
    return chunks


class LLMGateway:
    """Model gateway with retry, disk cache and per-run token logging."""

    def __init__(
        self,
        config: ClaimLensConfig | None = None,
        run_dir: Path | str | None = None,
        cache_dir: Path | str | None = None,
    ) -> None:
        self.config = config or ClaimLensConfig.from_env()
        self.run_dir = Path(run_dir) if run_dir is not None else None
        default_cache = Path.home() / ".cache" / "claimlens" / "llm"
        self.cache_dir = Path(cache_dir or os.environ.get("CLAIMLENS_CACHE_DIR", default_cache))

    # -- public API ----------------------------------------------------

    def complete(
        self,
        task: str,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | type | None = None,
        tools: list[dict[str, Any]] | None = None,
        role: str = "agent",
    ) -> Any:
        """Call the configured model and return parsed JSON.

        Args:
            task: Stable task key (used for fake responses and logging).
            messages: Chat messages as ``[{"role": ..., "content": ...}]``.
                A ``system`` role message is supported.
            schema: Optional JSON schema (dict) or pydantic model class
                constraining the output.
            tools: Optional function-calling tool definitions.
            role: One of ``planner``, ``agent``, ``fast``.

        Returns:
            Parsed JSON (dict/list). Non-JSON text is wrapped as
            ``{"text": ...}``.

        Raises:
            RateLimitError: If the primary provider is rate-limited and
                no fallback provider/key is configured.
        """
        if role not in VALID_ROLES:
            raise ValueError(f"Unknown role {role!r}. Choose from {VALID_ROLES}.")
        provider = self.config.provider
        model = self.config.model_for_role(role, provider)
        schema_dict = self._schema_to_dict(schema)
        cache_key = self._cache_key(provider, model, messages, schema_dict, tools)
        cached = self._cache_read(cache_key)
        if cached is not None:
            self._log_call(
                task, role, provider, model, messages, cached, cached_hit=True, raw_text=""
            )
            return cached

        try:
            result, raw_text = self._call_provider(
                task, provider, model, messages, schema_dict, tools
            )
        except Exception as exc:
            fallback = self.config.fallback_for(provider) if is_rate_limit_error(exc) else None
            if fallback is None:
                raise
            fallback_model = self.config.model_for_role(role, fallback)
            fallback_key = self._cache_key(fallback, fallback_model, messages, schema_dict, tools)
            fallback_cached = self._cache_read(fallback_key)
            if fallback_cached is not None:
                self._log_call(
                    task,
                    role,
                    fallback,
                    fallback_model,
                    messages,
                    fallback_cached,
                    cached_hit=True,
                    raw_text="",
                )
                return fallback_cached
            result, raw_text = self._call_provider(
                task, fallback, fallback_model, messages, schema_dict, tools
            )
            provider, model, cache_key = fallback, fallback_model, fallback_key
        self._cache_write(cache_key, result)
        self._log_call(
            task, role, provider, model, messages, result, cached_hit=False, raw_text=raw_text
        )
        return result

    def _call_provider(
        self,
        task: str,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        tools: list[dict[str, Any]] | None,
    ) -> tuple[Any, str]:
        """Dispatch one attempt to the named provider."""
        if provider == "fake":
            result = self._fake_complete(task, schema)
            return result, json.dumps(result)
        if provider == "gemini":
            return self._gemini_complete(model, messages, schema, tools)
        if provider == "openrouter":
            return self._openrouter_complete(model, messages, schema, tools)
        if provider == "ollama":
            return self._ollama_complete(model, messages, schema, tools)
        raise ValueError(f"Unknown provider {provider!r}. Choose gemini, openrouter, ollama, fake.")

    # -- fake provider -------------------------------------------------

    def _fake_responses_path(self) -> Path:
        override = os.environ.get("CLAIMLENS_FAKE_RESPONSES")
        if override:
            return Path(override)
        here = Path(__file__).resolve()
        for parent in [here.parent, *here.parents]:
            candidate = parent / "tests" / "fixtures" / "fake_llm_responses.json"
            if candidate.exists():
                return candidate
        # Default location relative to the package (repo root layout).
        return here.parent.parent / "tests" / "fixtures" / "fake_llm_responses.json"

    def _fake_complete(self, task: str, schema: dict[str, Any] | None) -> Any:
        path = self._fake_responses_path()
        with path.open(encoding="utf-8") as f:
            canned = json.load(f)
        if task not in canned:
            raise KeyError(f"No fake LLM response for task {task!r} in {path}.")
        result = canned[task]
        if schema is not None:
            self._validate_against_schema(result, schema)
        return result

    # -- provider implementations --------------------------------------

    def _gemini_complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        tools: list[dict[str, Any]] | None,
    ) -> tuple[Any, str]:
        api_key = self.config.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        system_texts = [str(m["content"]) for m in messages if m.get("role") == "system"]
        contents = []
        for m in messages:
            if m.get("role") == "system":
                continue
            role = "model" if m.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": str(m.get("content", ""))}]})
        payload: dict[str, Any] = {"contents": contents}
        if system_texts:
            payload["system_instruction"] = {"parts": [{"text": "\n".join(system_texts)}]}
        generation_config: dict[str, Any] = {}
        if schema is not None:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = schema
        if generation_config:
            payload["generationConfig"] = generation_config
        if tools is not None:
            payload["tools"] = [{"functionDeclarations": tools}]
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            f":generateContent?key={api_key}"
        )
        data = self._post_with_retry(url, {}, payload)
        try:
            parts = data["candidates"][0]["content"]["parts"]
            raw_text = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected Gemini response shape: {data!r}") from e
        return self._parse_json_or_text(raw_text), raw_text

    def _openrouter_complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        tools: list[dict[str, Any]] | None,
    ) -> tuple[Any, str]:
        api_key = self.config.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set.")
        payload: dict[str, Any] = {"model": model, "messages": messages}
        if schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "response", "schema": schema},
            }
        if tools is not None:
            payload["tools"] = tools
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        data = self._post_with_retry(
            "https://openrouter.ai/api/v1/chat/completions", headers, payload
        )
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected OpenRouter response shape: {data!r}") from e
        if message.get("tool_calls"):
            return {"tool_calls": message["tool_calls"]}, json.dumps(message)
        raw_text = str(message.get("content") or "")
        return self._parse_json_or_text(raw_text), raw_text

    def _ollama_complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        schema: dict[str, Any] | None,
        tools: list[dict[str, Any]] | None,
    ) -> tuple[Any, str]:
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        payload: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        if schema is not None:
            payload["format"] = schema
        if tools is not None:
            payload["tools"] = tools
        data = self._post_with_retry(f"{host}/api/chat", {}, payload)
        message = data.get("message", {})
        if message.get("tool_calls"):
            return {"tool_calls": message["tool_calls"]}, json.dumps(message)
        raw_text = str(message.get("content") or "")
        return self._parse_json_or_text(raw_text), raw_text

    # -- helpers --------------------------------------------------------

    def _post_with_retry(self, url: str, headers: dict[str, str], payload: dict[str, Any]) -> Any:
        last_error: Exception | None = None
        last_status: int | None = None
        with httpx.Client(timeout=120.0) as client:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    resp = client.post(url, headers=headers, json=payload)
                except httpx.HTTPError as e:
                    last_error = e
                    last_status = None
                    self._sleep(attempt)
                    continue
                if resp.status_code in RETRY_STATUS:
                    last_status = resp.status_code
                    last_error = RuntimeError(
                        f"HTTP {resp.status_code} from {url}: {resp.text[:500]}"
                    )
                    self._sleep(attempt)
                    continue
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as e:
                    raise RuntimeError(
                        f"HTTP {resp.status_code} from {url}: {resp.text[:500]}"
                    ) from e
                return resp.json()
        if last_status == 429:
            raise RateLimitError(f"HTTP 429 from {url}: quota exhausted.") from last_error
        raise RuntimeError(f"Request to {url} failed after retries.") from last_error

    def _sleep(self, attempt: int) -> None:
        if os.environ.get("CLAIMLENS_NO_SLEEP"):
            return
        time.sleep(BASE_BACKOFF_S * (2**attempt))

    def _schema_to_dict(self, schema: dict[str, Any] | type | None) -> dict | None:
        if schema is None:
            return None
        if isinstance(schema, dict):
            return schema
        model_schema = getattr(schema, "model_json_schema", None)
        if callable(model_schema):
            return schema.model_json_schema()  # type: ignore[union-attr]
        raise TypeError("schema must be a dict, a pydantic model class, or None.")

    def _validate_against_schema(self, result: Any, schema: dict[str, Any]) -> None:
        # Lightweight check: required keys must be present for object schemas.
        if isinstance(result, dict) and isinstance(schema.get("required"), list):
            missing = [k for k in schema["required"] if k not in result]
            if missing:
                raise ValueError(f"Fake response missing required keys: {missing}.")

    def _parse_json_or_text(self, raw_text: str) -> Any:
        try:
            return json.loads(raw_text)
        except (json.JSONDecodeError, TypeError):
            return {"text": raw_text}

    def _cache_key(
        self,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        schema: dict | None,
        tools: list[dict[str, Any]] | None,
    ) -> str:
        blob = json.dumps(
            {
                "model": model,
                "provider": provider,
                "messages": messages,
                "schema": schema,
                "tools": tools,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def _cache_read(self, key: str) -> Any | None:
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None
        try:
            with path.open(encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def _cache_write(self, key: str, result: Any) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            with (self.cache_dir / f"{key}.json").open("w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        except OSError:
            pass

    def _log_call(
        self,
        task: str,
        role: str,
        provider: str,
        model: str,
        messages: list[dict[str, Any]],
        result: Any,
        cached_hit: bool,
        raw_text: str,
    ) -> None:
        if self.run_dir is None:
            return
        try:
            self.run_dir.mkdir(parents=True, exist_ok=True)
            prompt_tokens = _approx_tokens(_messages_text(messages))
            completion_tokens = _approx_tokens(
                raw_text if isinstance(raw_text, str) else json.dumps(result)
            )
            entry = {
                "task": task,
                "role": role,
                "model": model,
                "provider": provider,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cached": cached_hit,
            }
            with (self.run_dir / "llm_log.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass
