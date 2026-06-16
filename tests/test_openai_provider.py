"""Tests for OpenAIProvider — all HTTP calls are mocked, no live API key required."""
import json
from unittest.mock import patch, MagicMock

import httpx
import pytest

from src.llm.openai_provider import OpenAIProvider, _encode_image_content
from src.llm.provider_base import (
    LLMTextResult, LLMJsonResult, LLMImageCompareResult, LLMVideoCompareResult,
)


def _make_response(status_code=200, json_body=None):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = json_body or {}
    if status_code >= 400:
        request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=request, response=resp
        )
    else:
        resp.raise_for_status.side_effect = None
    return resp


def _chat_completion(content: str, usage: dict | None = None) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": usage or {"prompt_tokens": 1, "completion_tokens": 1},
    }


def test_constructor_accepts_api_key():
    provider = OpenAIProvider(api_key="sk-test-123")
    assert provider.api_key == "sk-test-123"
    assert provider.provider_name == "openai"


def test_constructor_falls_back_to_env_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env-key")
    provider = OpenAIProvider()
    assert provider.api_key == "sk-env-key"


def test_complete_text_returns_llm_text_result():
    provider = OpenAIProvider(api_key="sk-test")
    body = _chat_completion("hello world")
    with patch("httpx.post", return_value=_make_response(200, body)) as mock_post:
        result = provider.complete_text("say hello", system_prompt="be nice")
    assert isinstance(result, LLMTextResult)
    assert result.text == "hello world"
    assert result.provider_name == "openai"
    assert result.model_name == provider.text_model
    assert result.usage == body["usage"]

    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["model"] == provider.text_model
    assert sent_payload["messages"][0] == {"role": "system", "content": "be nice"}
    assert sent_payload["messages"][1] == {"role": "user", "content": "say hello"}


def test_complete_text_without_system_prompt_omits_system_message():
    provider = OpenAIProvider(api_key="sk-test")
    body = _chat_completion("hi")
    with patch("httpx.post", return_value=_make_response(200, body)) as mock_post:
        provider.complete_text("hi there")
    sent_payload = mock_post.call_args.kwargs["json"]
    assert len(sent_payload["messages"]) == 1
    assert sent_payload["messages"][0]["role"] == "user"


def test_extract_json_parses_valid_json():
    provider = OpenAIProvider(api_key="sk-test")
    body = _chat_completion(json.dumps({"foo": "bar"}))
    with patch("httpx.post", return_value=_make_response(200, body)) as mock_post:
        result = provider.extract_json("extract this", schema_hint="{foo: string}")
    assert isinstance(result, LLMJsonResult)
    assert result.data == {"foo": "bar"}
    assert result.raw_text == json.dumps({"foo": "bar"})

    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["response_format"] == {"type": "json_object"}
    assert "{foo: string}" in sent_payload["messages"][0]["content"]


def test_extract_json_fallback_on_parse_failure():
    provider = OpenAIProvider(api_key="sk-test")
    body = _chat_completion("not valid json")
    with patch("httpx.post", return_value=_make_response(200, body)):
        result = provider.extract_json("extract this")
    assert result.data["_error"] == "JSON parse failed"
    assert result.data["_raw"] == "not valid json"


def test_compare_images_with_url(monkeypatch):
    provider = OpenAIProvider(api_key="sk-test")
    body = _chat_completion(json.dumps({"match": True}))
    with patch("httpx.post", return_value=_make_response(200, body)) as mock_post:
        result = provider.compare_images(
            ["https://example.com/a.jpg"], "do these match?"
        )
    assert isinstance(result, LLMImageCompareResult)
    assert result.result_json == {"match": True}
    assert result.model_name == provider.vision_model

    sent_payload = mock_post.call_args.kwargs["json"]
    assert sent_payload["model"] == provider.vision_model
    content = sent_payload["messages"][-1]["content"]
    assert content[0]["image_url"]["url"] == "https://example.com/a.jpg"
    assert content[-1] == {"type": "text", "text": "do these match?"}


def test_compare_images_with_local_file(tmp_path):
    img_path = tmp_path / "test.jpg"
    img_path.write_bytes(b"\xff\xd8\xff\xe0fakejpegdata")

    provider = OpenAIProvider(api_key="sk-test")
    body = _chat_completion(json.dumps({"match": False}))
    with patch("httpx.post", return_value=_make_response(200, body)) as mock_post:
        result = provider.compare_images([str(img_path)], "compare")
    assert result.result_json == {"match": False}

    sent_payload = mock_post.call_args.kwargs["json"]
    content = sent_payload["messages"][-1]["content"]
    assert content[0]["image_url"]["url"].startswith("data:image/jpg;base64,")


def test_encode_image_content_url_passthrough():
    encoded = _encode_image_content("http://example.com/x.png")
    assert encoded == {"type": "image_url", "image_url": {"url": "http://example.com/x.png"}}


def test_compare_video_frames_delegates_to_compare_images():
    provider = OpenAIProvider(api_key="sk-test")
    body = _chat_completion(json.dumps({"defect": False}))
    with patch("httpx.post", return_value=_make_response(200, body)):
        result = provider.compare_video_frames(
            ["https://example.com/f1.jpg", "https://example.com/f2.jpg"], "any defects?"
        )
    assert isinstance(result, LLMVideoCompareResult)
    assert result.result_json == {"defect": False}
    assert result.frames_used == 2
    assert result.model_name == provider.vision_model


def test_post_raises_runtime_error_on_4xx_without_retry():
    provider = OpenAIProvider(api_key="sk-test")
    with patch("httpx.post", return_value=_make_response(400, {})) as mock_post:
        with pytest.raises(RuntimeError, match="rejected the request"):
            provider.complete_text("hello")
    assert mock_post.call_count == 1


def test_post_retries_on_5xx_then_raises():
    provider = OpenAIProvider(api_key="sk-test")
    provider._retries = 2
    with patch("httpx.post", return_value=_make_response(500, {})) as mock_post, \
            patch("time.sleep", return_value=None):
        with pytest.raises(RuntimeError, match="failed after"):
            provider.complete_text("hello")
    assert mock_post.call_count == provider._retries + 1


def test_post_succeeds_after_transient_failure():
    provider = OpenAIProvider(api_key="sk-test")
    provider._retries = 2
    success_body = _chat_completion("recovered")
    responses = [_make_response(500, {}), _make_response(200, success_body)]
    with patch("httpx.post", side_effect=responses), patch("time.sleep", return_value=None):
        result = provider.complete_text("hello")
    assert result.text == "recovered"
