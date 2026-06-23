"""Tests for OperatorLLMApiRuntime guard: disabled-by-default, token gate, no token leakage."""
from __future__ import annotations

import pytest

from src.gpm.qwen.operator_llm_api_runtime import OperatorLLMApiRuntime
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig


def test_llm_api_disabled_raises() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=False,
        qwen_api_key="sk-test",
    )
    with pytest.raises(RuntimeError, match="disabled"):
        OperatorLLMApiRuntime(config)


def test_llm_api_missing_token_raises() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        qwen_api_key=None,
    )
    with pytest.raises(RuntimeError, match="QWEN_API_KEY"):
        OperatorLLMApiRuntime(config)


def test_llm_api_skipped_when_env_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """When neither GPM_ENABLE_QWEN_LLM_API nor QWEN_API_KEY are set, runtime raises."""
    monkeypatch.delenv("GPM_ENABLE_QWEN_LLM_API", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    config = QwenRuntimeConfig.from_env()
    # In mock mode by default, so no error from config itself.
    # But if forced to llm_api:
    bad_config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=False,
        qwen_api_key=None,
    )
    with pytest.raises(RuntimeError, match="disabled"):
        OperatorLLMApiRuntime(bad_config)


def test_llm_api_does_not_log_token(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture) -> None:
    """Token must not appear in config repr or redacted output."""
    monkeypatch.setenv("QWEN_API_KEY", "sk-supersecret-123abc")
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
        qwen_api_key="sk-test",
        llm_provider="nonexistent_provider",
    )
    with pytest.raises(RuntimeError, match="Unknown LLM provider"):
        OperatorLLMApiRuntime(config)


def test_valid_config_constructs_without_network_call() -> None:
    """OperatorLLMApiRuntime init must not make network calls."""
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        qwen_api_key="sk-test-no-network",
        llm_provider="qwen",
    )
    runtime = OperatorLLMApiRuntime(config)
    assert runtime.runtime_mode == "llm_api"
    assert runtime.provider_name == "qwen"
