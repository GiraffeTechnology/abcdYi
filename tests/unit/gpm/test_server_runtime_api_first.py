"""Tests: profile-based runtime resolution via QwenRuntimeResolver.

Both lightweight and server profiles use local-first resolution:
  MNN (if path configured) → LLM API (if operator allows) → hard fail.
LLM API is always operator opt-in; never called without enable_llm_api=True + token.
Neither profile ever falls back to mock silently.
"""
from __future__ import annotations

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


def test_lightweight_profile_from_env_defaults_to_auto(monkeypatch):
    monkeypatch.setenv("GPM_RUNTIME_PROFILE", "lightweight")
    monkeypatch.delenv("GPM_LLM_RUNTIME_MODE", raising=False)
    monkeypatch.delenv("GPM_QWEN_RUNTIME_MODE", raising=False)
    config = QwenRuntimeConfig.from_env()
    assert config.runtime_mode == "auto"
    assert config.runtime_profile == "lightweight"


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
# Resolver: local/ci + auto → mock (CI-safe)
# ---------------------------------------------------------------------------


def test_local_auto_resolves_to_mock():
    config = QwenRuntimeConfig(runtime_mode="auto", runtime_profile="local")
    runtime = resolve_runtime(config)
    assert runtime.runtime_mode == "mock"


def test_ci_auto_resolves_to_mock():
    config = QwenRuntimeConfig(runtime_mode="auto", runtime_profile="ci")
    runtime = resolve_runtime(config)
    assert runtime.runtime_mode == "mock"


# ---------------------------------------------------------------------------
# Resolver: lightweight + auto → local-first, hard fail when no runtime callable
# ---------------------------------------------------------------------------


def test_lightweight_auto_no_runtime_raises_unavailable():
    """No MNN path, API not enabled → hard fail."""
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="lightweight",
        enable_llm_api=False,
        llm_api_key=None,
    )
    with pytest.raises(GPMRuntimeUnavailableError):
        resolve_runtime(config)


def test_lightweight_auto_missing_token_raises_unavailable():
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="lightweight",
        enable_llm_api=True,
        llm_api_key=None,
    )
    with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
        resolve_runtime(config)
    assert exc_info.value.reason == "missing_token"


def test_lightweight_does_not_silently_fall_back_to_mock():
    """lightweight + auto with no callable runtime must raise, never return mock."""
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="lightweight",
        enable_llm_api=False,
        llm_api_key=None,
    )
    with pytest.raises(GPMRuntimeUnavailableError):
        resolve_runtime(config)


def test_lightweight_auto_prefers_mnn_over_api():
    """MNN path configured and succeeds → returned as preferred local runtime."""
    from unittest.mock import MagicMock, patch

    mock_mnn = MagicMock()
    mock_mnn.runtime_mode = "mnn"

    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="lightweight",
        enable_llm_api=True,
        llm_api_key="sk-valid-token",
        mnn_model_path="/models/qwen.mnn",
    )

    with patch(
        "src.gpm.llm_adapters.qwen_local_runtime.QwenLocalRuntime",
        return_value=mock_mnn,
    ) as mock_cls:
        result = resolve_runtime(config)

    # Only the MNN init fires; API never called
    assert mock_cls.call_count == 1
    assert mock_cls.call_args.kwargs["config"].runtime_mode == "mnn"
    assert result.runtime_mode == "mnn"


# ---------------------------------------------------------------------------
# Resolver: server + auto → local-first, hard fail when no runtime callable
# ---------------------------------------------------------------------------


def test_server_auto_missing_token_raises_unavailable():
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="server",
        enable_llm_api=True,
        llm_api_key=None,
    )
    with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
        resolve_runtime(config)
    err = exc_info.value
    assert err.reason == "missing_token"
    assert "GPM_LLM_API_KEY" in err.safe_message
    assert err.operator_action_required is True


def test_server_auto_api_disabled_raises_unavailable():
    """Token present but enable_llm_api=False → api_disabled, token not in message."""
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
    """server + auto with no callable runtime must raise, never return mock."""
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="server",
        enable_llm_api=False,
        llm_api_key=None,
    )
    with pytest.raises(GPMRuntimeUnavailableError):
        resolve_runtime(config)


def test_server_auto_with_no_mnn_falls_to_api():
    """No MNN path → step 1 skipped; resolver falls through to API step."""
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
        "src.gpm.llm_adapters.qwen_local_runtime.QwenLocalRuntime",
        return_value=mock_runtime,
    ):
        result = resolve_runtime(config)

    assert result.runtime_mode == "llm_api"


def test_server_auto_prefers_mnn_over_api():
    """MNN path configured and succeeds → API is never called."""
    from unittest.mock import MagicMock, patch

    mock_mnn = MagicMock()
    mock_mnn.runtime_mode = "mnn"

    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="server",
        enable_llm_api=True,
        llm_api_key="sk-valid-token",
        mnn_model_path="/models/qwen.mnn",
    )

    with patch(
        "src.gpm.llm_adapters.qwen_local_runtime.QwenLocalRuntime",
        return_value=mock_mnn,
    ) as mock_cls:
        result = resolve_runtime(config)

    # Only the MNN init fires; API never called
    assert mock_cls.call_count == 1
    assert mock_cls.call_args.kwargs["config"].runtime_mode == "mnn"
    assert result.runtime_mode == "mnn"
