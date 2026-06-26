"""Tests for OperatorLLMApiRuntime guard: disabled-by-default, token gate, no token leakage."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.gpm.qwen.gpm_runtime_unavailable_error import GPMRuntimeUnavailableError
from src.gpm.qwen.operator_llm_api_runtime import OperatorLLMApiRuntime
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig


def _enabled_config(**kwargs) -> QwenRuntimeConfig:
    return QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        llm_api_key="sk-test",
        llm_provider="qwen",
        **kwargs,
    )


def test_llm_api_disabled_raises() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=False,
        llm_api_key="sk-test",
    )
    with pytest.raises(RuntimeError, match="disabled"):
        OperatorLLMApiRuntime(config)


def test_llm_api_missing_token_raises() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        llm_api_key=None,
    )
    with pytest.raises(RuntimeError, match="GPM_LLM_API_KEY"):
        OperatorLLMApiRuntime(config)


def test_llm_api_skipped_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """When neither GPM_ENABLE_LLM_API nor GPM_LLM_API_KEY are set, runtime raises."""
    monkeypatch.delenv("GPM_ENABLE_LLM_API", raising=False)
    monkeypatch.delenv("GPM_ENABLE_QWEN_LLM_API", raising=False)
    monkeypatch.delenv("GPM_LLM_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    bad_config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=False,
        llm_api_key=None,
    )
    with pytest.raises(RuntimeError, match="disabled"):
        OperatorLLMApiRuntime(bad_config)


def test_llm_api_does_not_log_token(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Token must not appear in config repr or redacted output."""
    monkeypatch.setenv("GPM_LLM_API_KEY", "sk-supersecret-123abc")
    config = QwenRuntimeConfig.from_env()
    redacted = config.redacted()
    captured = capsys.readouterr()
    assert "sk-supersecret-123abc" not in str(redacted)
    assert "sk-supersecret-123abc" not in captured.out
    assert "sk-supersecret-123abc" not in captured.err


def test_runtime_mode_is_llm_api() -> None:
    assert OperatorLLMApiRuntime.runtime_mode == "llm_api"


def test_unknown_provider_raises() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        llm_api_key="sk-test",
        llm_provider="nonexistent_provider",
    )
    with pytest.raises(RuntimeError, match="Unknown LLM provider"):
        OperatorLLMApiRuntime(config)


def test_valid_config_constructs_without_network_call() -> None:
    """OperatorLLMApiRuntime init must not make network calls."""
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        llm_api_key="sk-test-no-network",
        llm_provider="qwen",
    )
    runtime = OperatorLLMApiRuntime(config)
    assert runtime.runtime_mode == "llm_api"
    assert runtime.provider_name == "qwen"


# ── HTTPStatusError → GPMRuntimeUnavailableError (no unhandled 500) ──────────

def _make_http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(f"HTTP {status_code}", request=request, response=response)


def test_invalid_key_401_raises_runtime_unavailable() -> None:
    """401 from provider must raise GPMRuntimeUnavailableError, not propagate raw httpx error."""
    runtime = OperatorLLMApiRuntime(_enabled_config())
    with patch.object(runtime._provider, "generate_json", side_effect=_make_http_status_error(401)):
        with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
            runtime.generate_json("prompt", "schema")
    assert exc_info.value.operator_action_required is True
    assert "401" in exc_info.value.safe_message or "rejected" in exc_info.value.safe_message


def test_rate_limit_429_raises_runtime_unavailable() -> None:
    """429 from provider must raise GPMRuntimeUnavailableError with rate-limit message."""
    runtime = OperatorLLMApiRuntime(_enabled_config())
    with patch.object(runtime._provider, "generate_json", side_effect=_make_http_status_error(429)):
        with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
            runtime.generate_json("prompt", "schema")
    assert "429" in exc_info.value.safe_message or "rate limit" in exc_info.value.safe_message.lower()


def test_provider_5xx_raises_runtime_unavailable() -> None:
    """5xx from provider must raise GPMRuntimeUnavailableError, not raw httpx error."""
    runtime = OperatorLLMApiRuntime(_enabled_config())
    with patch.object(runtime._provider, "generate_json", side_effect=_make_http_status_error(503)):
        with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
            runtime.generate_json("prompt", "schema")
    assert exc_info.value.operator_action_required is True


def test_http_status_error_does_not_leak_token() -> None:
    """Error message must not contain the API key value."""
    token = "sk-SECRET-CANARY-VALUE-XYZ"
    config = QwenRuntimeConfig(
        runtime_mode="llm_api", enable_llm_api=True, llm_api_key=token, llm_provider="qwen"
    )
    runtime = OperatorLLMApiRuntime(config)
    with patch.object(runtime._provider, "generate_json", side_effect=_make_http_status_error(401)):
        with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
            runtime.generate_json("prompt", "schema")
    assert token not in exc_info.value.safe_message
    assert token not in exc_info.value.reason


def test_connect_error_raises_runtime_unavailable() -> None:
    """Network unreachable must raise GPMRuntimeUnavailableError — no unhandled ConnectError."""
    runtime = OperatorLLMApiRuntime(_enabled_config())
    request = httpx.Request("POST", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
    with patch.object(runtime._provider, "generate_json",
                      side_effect=httpx.ConnectError("Connection refused", request=request)):
        with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
            runtime.generate_json("prompt", "schema")
    assert exc_info.value.operator_action_required is True
