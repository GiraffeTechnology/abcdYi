"""Tests for QwenRuntimeConfig: env loading, token redaction, canonical env priority."""
from __future__ import annotations

import pytest

from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig


def test_default_runtime_mode_is_mock() -> None:
    config = QwenRuntimeConfig()
    assert config.runtime_mode == "mock"


def test_from_env_default_is_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GPM_LLM_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("GPM_QWEN_RUNTIME_MODE", raising=False)
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "mock"


def test_from_env_reads_runtime_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """Canonical GPM_LLM_RUNTIME_MODE must be read."""
    monkeypatch.setenv("GPM_LLM_RUNTIME_MODE", "llm_api")
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "llm_api"


def test_from_env_invalid_mode_falls_back_to_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GPM_LLM_RUNTIME_MODE", "cloud_magic")
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "mock"


def test_canonical_runtime_mode_takes_priority_over_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """GPM_LLM_RUNTIME_MODE beats GPM_QWEN_RUNTIME_MODE when both are set."""
    monkeypatch.setenv("GPM_LLM_RUNTIME_MODE", "llm_api")
    monkeypatch.setenv("GPM_QWEN_RUNTIME_MODE", "mock")
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "llm_api"


def test_qwen_runtime_mode_alias_works_as_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """GPM_QWEN_RUNTIME_MODE works when GPM_LLM_RUNTIME_MODE is not set."""
    monkeypatch.delenv("GPM_LLM_RUNTIME_MODE", raising=False)
    monkeypatch.setenv("GPM_QWEN_RUNTIME_MODE", "llm_api")
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "llm_api"


def test_api_token_not_in_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GPM_LLM_API_KEY", "sk-supersecret-token-abc123")
    config = QwenRuntimeConfig.from_env()
    assert config.llm_api_key == "sk-supersecret-token-abc123"
    redacted = config.redacted()
    assert "sk-supersecret-token-abc123" not in str(redacted)
    assert redacted["llm_api_key"] == "***REDACTED***"


def test_redacted_shows_none_when_no_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GPM_LLM_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.delenv("DASHSCOPE_API_KEY", raising=False)
    config = QwenRuntimeConfig.from_env()
    redacted = config.redacted()
    assert redacted["llm_api_key"] is None


def test_canonical_llm_api_key_takes_priority_over_qwen_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    """GPM_LLM_API_KEY beats QWEN_API_KEY when both are set."""
    monkeypatch.setenv("GPM_LLM_API_KEY", "canonical-key-aaa")
    monkeypatch.setenv("QWEN_API_KEY", "alias-key-bbb")
    config = QwenRuntimeConfig.from_env()
    assert config.llm_api_key == "canonical-key-aaa"


def test_qwen_alias_llm_api_key_works_as_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """QWEN_API_KEY works when GPM_LLM_API_KEY is not set."""
    monkeypatch.delenv("GPM_LLM_API_KEY", raising=False)
    monkeypatch.setenv("QWEN_API_KEY", "qwen-fallback-token")
    config = QwenRuntimeConfig.from_env()
    assert config.llm_api_key == "qwen-fallback-token"


def test_dashscope_api_key_used_as_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GPM_LLM_API_KEY", raising=False)
    monkeypatch.delenv("QWEN_API_KEY", raising=False)
    monkeypatch.setenv("DASHSCOPE_API_KEY", "dashscope-tok-xyz")
    config = QwenRuntimeConfig.from_env()
    assert config.llm_api_key == "dashscope-tok-xyz"


def test_enable_llm_api_false_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GPM_ENABLE_LLM_API", raising=False)
    monkeypatch.delenv("GPM_ENABLE_QWEN_LLM_API", raising=False)
    config = QwenRuntimeConfig.from_env()
    assert config.enable_llm_api is False


def test_enable_llm_api_set_by_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Canonical GPM_ENABLE_LLM_API must enable LLM API mode."""
    monkeypatch.setenv("GPM_ENABLE_LLM_API", "true")
    config = QwenRuntimeConfig.from_env()
    assert config.enable_llm_api is True


def test_canonical_enable_llm_api_takes_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """GPM_ENABLE_LLM_API=true beats GPM_ENABLE_QWEN_LLM_API=false."""
    monkeypatch.setenv("GPM_ENABLE_LLM_API", "true")
    monkeypatch.setenv("GPM_ENABLE_QWEN_LLM_API", "false")
    config = QwenRuntimeConfig.from_env()
    assert config.enable_llm_api is True


def test_qwen_enable_alias_works_as_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GPM_ENABLE_LLM_API", raising=False)
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
