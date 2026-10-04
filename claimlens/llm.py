"""Single model gateway for ClaimLens.

All model calls in the codebase go through this module. No other file
imports a model SDK; providers are reached over HTTP with httpx.

Providers: ``gemini``, ``openrouter``, ``ollama`` and ``fake``.
The ``fake`` provider returns canned JSON from
``tests/fixtures/fake_llm_responses.json`` keyed by ``task``, so tests
run without an API key.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx

from claimlens.config import ClaimLensConfig

VALID_ROLES = ("planner", "agent", "fast")
RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
BASE_BACKOFF_S = 1.0


def _approx_tokens(text: str) -> int:
    """Rough token estimate used when a provider reports no usage."""
    return max(1, len(text) // 4)


def approx_tokens(text: str) -> int:
    """Public rough token estimate (characters / 4) for chunking decisions."""
    return _approx_tokens(text)


def _block_text(content: Any) -> str:
    """Text of one message's content, ignoring image blocks.

    Content is usually a string; it may also be a list of blocks like
    ``{"text": ...}`` and ``{"image": {"mime": ..., "b64": ...}}`` used
    for vision calls. Image bytes never count as text (they would
    inflate token estimates by megabytes).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = [str(block.get("text", "")) for block in content if isinstance(block, dict)]
        return "\n".join(text for text in texts if text)
    return str(content)


def _messages_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(_block_text(m.get("content", "")) for m in messages)


def _json_spans(text: str) -> list[tuple[int, int]]:
    """Balanced ``{...}`` / ``[...]`` spans, largest first, strings respected."""
    spans: list[tuple[int, int]] = []
    for i, ch in enumerate(text):
        if ch not in "{[":
            continue
        depth = 0
        in_str = False
        esc = False
        for j in range(i, len(text)):
            c = text[j]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c in "{[":
                depth += 1
            elif c in "}]":
                depth -= 1
                if depth == 0:
                    spans.append((i, j + 1))
                    break
    spans.sort(key=lambda span: span[1] - span[0], reverse=True)
    return spans


def _gemini_parts(content: Any) -> list[dict[str, Any]]:
    """Translate message content into Gemini request parts.

    Plain strings become one text part (unchanged behavior). Lists may
    mix ``{"text": ...}`` blocks with ``{"image": {"mime": ...,
    "b64": ...}}`` blocks, which become ``inlineData`` parts so page
    images travel as vision input instead of base64 text.
    """
    if isinstance(content, str):
        return [{"text": content}]
    if isinstance(content, list):
        parts: list[dict[str, Any]] = []
        for block in content:
            if not isinstance(block, dict):
                parts.append({"text": str(block)})
            elif "image" in block and isinstance(block["image"], dict):
                image = block["image"]
                parts.append(
                    {
                        "inlineData": {
                            "mimeType": str(image.get("mime", "image/png")),
                            "data": str(image.get("b64", "")),
                        }
                    }
                )
            else:
                parts.append({"text": str(block.get("text", ""))})
        return parts or [{"text": ""}]
    return [{"text": str(content)}]


def _text_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copy messages with block content flattened to text.

    Providers without image-part support receive the text blocks only;
    image blocks become a short placeholder so nothing large leaks.
    """
    flat = []
    for message in messages:
        content = message.get("content", "")
        if isinstance(content, list):
            texts = [str(block.get("text", "")) for block in content if isinstance(block, dict)]
            if any(isinstance(block, dict) and "image" in block for block in content):
                texts.append("[image omitted: provider has no image-part support]")
            content = "\n".join(text for text in texts if text)
        flat.append({**message, "content": content})
    return flat


def _cacheable(result: Any, schema: dict | None) -> bool:
    """Whether a gateway result may be written to the disk cache.

    A ``{"text": ...}`` fallback against a requested schema means the
    output failed to parse; caching it would poison stage retry loops,
    which re-issue identical prompts and would replay the same garbage.
    Schema-free text answers are still cached.
    """
    if schema is None:
        return True
    return not (isinstance(result, dict) and set(result) == {"text"})


def _extract_json(text: str) -> Any:
    """Parse model output as JSON, tolerating fences and chatter.

    Tries the stripped text, then markdown-fence stripping, then the
    largest balanced JSON substring. Raises ``ValueError`` when nothing
    parses, so callers can fall back to ``{"text": ...}``.
    """
    stripped = text.strip()
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        pass
    fenced = stripped
    if fenced.startswith("```"):
        fenced = fenced.split("\n", 1)[1] if "\n" in fenced else ""
    if fenced.rstrip().endswith("```"):
        fenced = fenced.rstrip()[:-3]
    try:
        return json.loads(fenced.strip())
    except (json.JSONDecodeError, ValueError):
        pass
    for start, end in _json_spans(stripped):
        try:
            parsed = json.loads(stripped[start:end])
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, (dict, list)):
            return parsed
    raise ValueError("No JSON object found in model output.")


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
        """
        if role not in VALID_ROLES:
            raise ValueError(f"Unknown role {role!r}. Choose from {VALID_ROLES}.")
        model = self.config.model_for_role(role)
        schema_dict = self._schema_to_dict(schema)
        cache_key = self._cache_key(model, messages, schema_dict, tools)
        cached = self._cache_read(cache_key)
        if cached is not None:
            self._log_call(task, role, model, messages, cached, cached_hit=True, raw_text="")
            return cached

        provider = self.config.provider
        if provider == "fake":
            result = self._fake_complete(task, schema_dict)
            raw_text = json.dumps(result)
        elif provider == "gemini":
            result, raw_text = self._gemini_complete(model, messages, schema_dict, tools)
        elif provider == "openrouter":
            result, raw_text = self._openrouter_complete(model, messages, schema_dict, tools)
        elif provider == "ollama":
            result, raw_text = self._ollama_complete(model, messages, schema_dict, tools)
        else:
            raise ValueError(
                f"Unknown provider {provider!r}. Choose gemini, openrouter, ollama, fake."
            )
        if _cacheable(result, schema_dict):
            self._cache_write(cache_key, result)
        self._log_call(task, role, model, messages, result, cached_hit=False, raw_text=raw_text)
        return result

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
        system_texts = [_block_text(m["content"]) for m in messages if m.get("role") == "system"]
        contents = []
        for m in messages:
            if m.get("role") == "system":
                continue
            role = "model" if m.get("role") == "assistant" else "user"
            contents.append({"role": role, "parts": _gemini_parts(m.get("content", ""))})
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
            # Thinking models narrate tool use instead of calling; ANY
            # forces real function calls. The agent finishes through the
            # report_result tool, so no plain-text finish is needed.
            payload["toolConfig"] = {"functionCallingConfig": {"mode": "ANY"}}
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            f":generateContent?key={api_key}"
        )
        data = self._post_with_retry(url, {}, payload)
        try:
            parts = data["candidates"][0]["content"]["parts"]
            calls = [
                {
                    "name": p["functionCall"].get("name", ""),
                    "arguments": p["functionCall"].get("args", {}),
                }
                for p in parts
                if isinstance(p, dict) and isinstance(p.get("functionCall"), dict)
            ]
            calls = [call for call in calls if call["name"]]
            raw_text = "".join(str(p.get("text", "")) for p in parts if isinstance(p, dict))
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected Gemini response shape: {data!r}") from e
        if calls:
            return {"tool_calls": calls, "text": raw_text}, json.dumps(
                {"tool_calls": calls, "text": raw_text}
            )
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
        payload: dict[str, Any] = {"model": model, "messages": _text_messages(messages)}
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
        payload: dict[str, Any] = {
            "model": model,
            "messages": _text_messages(messages),
            "stream": False,
        }
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
        # Thinking models deliberate for minutes before answering; a short
        # timeout would abort healthy turns and burn quota on retries.
        display_url = re.sub(r"([?&]key=)[^&]*", r"\1<redacted>", url)
        with httpx.Client(timeout=600.0) as client:
            for attempt in range(MAX_RETRIES + 1):
                try:
                    resp = client.post(url, headers=headers, json=payload)
                except httpx.HTTPError as e:
                    last_error = e
                    self._sleep(attempt)
                    continue
                if resp.status_code in RETRY_STATUS:
                    last_error = RuntimeError(
                        f"HTTP {resp.status_code} from {display_url}: {resp.text[:500]}"
                    )
                    self._sleep(attempt)
                    continue
                try:
                    resp.raise_for_status()
                except httpx.HTTPStatusError as e:
                    raise RuntimeError(
                        f"HTTP {resp.status_code} from {display_url}: {resp.text[:500]}"
                    ) from e
                return resp.json()
        raise RuntimeError(f"Request to {display_url} failed after retries.") from last_error

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
            return _extract_json(raw_text)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {"text": raw_text}

    def _cache_key(
        self,
        model: str,
        messages: list[dict[str, Any]],
        schema: dict | None,
        tools: list[dict[str, Any]] | None,
    ) -> str:
        blob = json.dumps(
            {
                "model": model,
                "provider": self.config.provider,
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
                "provider": self.config.provider,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cached": cached_hit,
            }
            with (self.run_dir / "llm_log.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass
