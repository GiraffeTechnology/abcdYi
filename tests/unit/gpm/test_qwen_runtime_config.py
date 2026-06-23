"""Tests for QwenRuntimeConfig: env loading, token redaction, guards."""
from __future__ import annotations

import os

import pytest

from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig


def test_default_runtime_mode_is_mock() -> None:
    config = QwenRuntimeConfig()
    assert config.runtime_mode == "mock"


def test_from_env_default_is_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GPM_QWEN_RUNTIME_MODE", raising=False)
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "mock"


def test_from_env_reads_runtime_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GPM_QWEN_RUNTIME_MODE", "llm_api")
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "llm_api"


def test_from_env_invalid_mode_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GPM_QWEN_RUNTIME_MODE", "cloud_magic")
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "mock"


def test_api_token_not_in_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QWEN_API_KEY", "sk-supersecret-token-abc123")
    config = QwenRuntimeConfig.from_env()
    redacted = config.redacted()
    assert "sk-supersecret-token-abc123" not in str(redacted)
    assert redacted["llm_api_key"] == "***REDACTED***"


def test_redacted_shows_none_when_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    config = QwenRuntimeConfig.from_env()
    redacted = config.redacted()
    assert redacted["llm_api_key"] is None


def test_dashscope_api_key_used_as_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-tok-xyz")
    config = QwenRuntimeConfig.from_env()
    assert config.qwen_api_key == "dashscope-tok-xyz"


def test_enable_llm_api_false_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GPM_ENABLE_QWEN_LLM_API", raising=False)
    config = QwenRuntimeConfig.from_env()
    assert config.enable_llm_api is False


def test_enable_llm_api_set_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GPM_ENABLE_QWEN_LLM_API", "true")
    config = QwenRuntimeConfig.from_env()
    assert config.enable_llm_api is True


def test_config_is_frozen() -> None:
    config = QwenRuntimeConfig()
    with pytest.raises((AttributeError, TypeError)):
        config.runtime_mode = "mnn"  # type: ignore[misc]


def test_mnn_model_path_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GPM_QWEN_MNN_MODEL_PATH", "/models/qwen.mnn")
    config = QwenRuntimeConfig.from_env()
    assert config.mnn_model_path == "/models/qwen.mnn"
