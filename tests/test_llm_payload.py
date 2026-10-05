"""Gateway robustness tests: fenced JSON recovery and image parts (no network)."""

from __future__ import annotations

import pytest

from claimlens.llm import (
    _block_text,
    _cacheable,
    _extract_json,
    _gemini_parts,
    _text_messages,
)


def test_extract_json_clean() -> None:
    assert _extract_json('{"claims": []}') == {"claims": []}


def test_extract_json_strips_fences() -> None:
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('{"a": 1}\n```') == {"a": 1}


def test_extract_json_recovers_from_chatter() -> None:
    assert _extract_json('thoughts here {"a": 2} trailing') == {"a": 2}


def test_extract_json_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        _extract_json("no json at all")


def test_gemini_parts_string_unchanged() -> None:
    assert _gemini_parts("hello") == [{"text": "hello"}]


def test_gemini_parts_image_blocks() -> None:
    parts = _gemini_parts([{"text": "see image"}, {"image": {"mime": "image/png", "b64": "AAA"}}])
    assert parts[0] == {"text": "see image"}
    assert parts[1] == {"inlineData": {"mimeType": "image/png", "data": "AAA"}}


def test_block_text_ignores_images() -> None:
    content = [{"text": "hi"}, {"image": {"mime": "image/png", "b64": "A" * 1000}}]
    assert _block_text(content) == "hi"
    assert _block_text("plain") == "plain"


def test_text_messages_flatten_with_placeholder() -> None:
    messages = [{"role": "user", "content": [{"text": "hi"}, {"image": {"b64": "AA"}}]}]
    flat = _text_messages(messages)
    assert flat[0]["content"].startswith("hi")
    assert "image omitted" in flat[0]["content"]
    assert _text_messages([{"role": "user", "content": "x"}]) == [{"role": "user", "content": "x"}]


def test_unparseable_schema_output_is_not_cacheable() -> None:
    assert _cacheable({"text": "garbage"}, {"type": "object"}) is False
    assert _cacheable({"claims": []}, {"type": "object"}) is True
    assert _cacheable({"text": "plain answer"}, None) is True
