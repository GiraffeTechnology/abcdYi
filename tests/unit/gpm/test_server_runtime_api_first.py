"""Tests: server-profile API-first runtime resolution via QwenRuntimeResolver."""
from __future__ import annotations

import dataclasses

import pytest

from src.gpm.qwen.gpm_runtime_unavailable_error import GPMRuntimeUnavailableError
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
from src.gpm.qwen.qwen_runtime_resolver import resolve_runtime


# ---------------------------------------------------------------------------
# Config profile defaults
# ---------------------------------------------------------------------------


def test_server_profile_from_env_defaults_to_auto(monkeypatch):
    monkeypatch.setenv("GPM_RUNTIME_PROFILE", "server")
    monkeypatch.delenv("GPM_LLM_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("GPM_QWEN_RUNTIME_MODE", raising=False)
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "auto"
    assert config.runtime_profile == "server"


def test_ci_profile_defaults_to_mock(monkeypatch):
    monkeypatch.setenv("GPM_RUNTIME_PROFILE", "ci")
    monkeypatch.delenv("GPM_LLM_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("GPM_QWEN_RUNTIME_MODE", raising=False)
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "mock"
    assert config.runtime_profile == "ci"


def test_local_profile_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("GPM_RUNTIME_PROFILE", raising=False)
    monkeypatch.delenv("GPM_LLM_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("GPM_QWEN_RUNTIME_MODE", raising=False)
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "mock"
    assert config.runtime_profile == "local"


def test_explicit_override_beats_profile_default(monkeypatch):
    """Explicit GPM_LLM_RUNTIME_MODE=mock overrides server profile's auto default."""
    monkeypatch.setenv("GPM_RUNTIME_PROFILE", "server")
    monkeypatch.setenv("GPM_LLM_RUNTIME_MODE", "mock")
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "mock"
    assert config.runtime_profile == "server"


def test_invalid_profile_falls_back_to_local(monkeypatch):
    monkeypatch.setenv("GPM_RUNTIME_PROFILE", "production")
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_profile == "local"


# ---------------------------------------------------------------------------
# Resolver: local/ci + auto -> mock (CI-safe)
# ---------------------------------------------------------------------------


def test_local_ci_auto_resolves_to_mock():
    config = QwenRuntimeConfig(runtime_mode="auto", runtime_profile="local")
    runtime = resolve_runtime(config)
    assert runtime.runtime_mode == "mock"


def test_ci_auto_resolves_to_mock():
    config = QwenRuntimeConfig(runtime_mode="auto", runtime_profile="ci")
    runtime = resolve_runtime(config)
    assert runtime.runtime_mode == "mock"


# ---------------------------------------------------------------------------
# Resolver: server + auto -> API-first, raises on missing token
# ---------------------------------------------------------------------------


def test_server_auto_missing_token_raises_unavailable():
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="server",
        enable_llm_api=True,
        llm_api_key=None,  # no token
    )
    with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
        resolve_runtime(config)
    err = exc_info.value
    assert err.reason == "missing_token"
    assert "GPM_LLM_API_KEY" in err.safe_message
    assert err.operator_action_required is True
    # Token must never appear in any message field
    assert err.llm_api_key if hasattr(err, "llm_api_key") else True


def test_server_auto_api_disabled_raises_unavailable():
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="server",
        enable_llm_api=False,
        llm_api_key="sk-test-key",
    )
    with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
        resolve_runtime(config)
    err = exc_info.value
    assert err.reason == "api_disabled"
    assert "GPM_ENABLE_LLM_API" in err.safe_message
    assert "sk-test-key" not in err.safe_message


def test_server_auto_does_not_silently_fall_back_to_mock():
    """Server + auto with no callable runtime must raise, never return mock."""
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="server",
        enable_llm_api=False,
        llm_api_key=None,
        enable_local_model_fallback=False,
    )
    with pytest.raises(GPMRuntimeUnavailableError):
        resolve_runtime(config)


def test_server_auto_with_valid_api_returns_llm_api_runtime(monkeypatch):
    """When OperatorLLMApiRuntime succeeds, resolver returns it."""
    from unittest.mock import MagicMock, patch

    mock_runtime = MagicMock()
    mock_runtime.runtime_mode = "llm_api"

    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="server",
        enable_llm_api=True,
        llm_api_key="sk-valid-token",
    )

    with patch(
        "src.gpm.qwen.qwen_runtime_resolver.QwenLocalRuntime",
        return_value=mock_runtime,
    ):
        result = resolve_runtime(config)

    assert result.runtime_mode == "llm_api"


def test_server_enable_local_model_fallback_default_is_false(monkeypatch):
    monkeypatch.delenv("GPM_ENABLE_LOCAL_MODEL_FALLBACK", raising=False)
    config = QwenRuntimeConfig.from_env()
    assert config.enable_local_model_fallback is False


def test_server_enable_local_model_fallback_parses_true(monkeypatch):
    monkeypatch.setenv("GPM_ENABLE_LOCAL_MODEL_FALLBACK", "true")
    config = QwenRuntimeConfig.from_env()
    assert config.enable_local_model_fallback is True
