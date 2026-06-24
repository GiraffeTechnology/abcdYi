"""Tests: GPMRuntimeUnavailableError shape, token safety, and resolver error paths."""
from __future__ import annotations

import pytest

from src.gpm.qwen.gpm_runtime_unavailable_error import GPMRuntimeUnavailableError
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
from src.gpm.qwen.qwen_runtime_resolver import resolve_runtime


# ---------------------------------------------------------------------------
# GPMRuntimeUnavailableError contract
# ---------------------------------------------------------------------------


def test_unavailable_error_to_status_shape():
    err = GPMRuntimeUnavailableError(
        reason="missing_token",
        attempted_runtime="llm_api",
        provider="qwen",
        safe_message="LLM API unavailable: GPM_LLM_API_KEY is missing. Skipping LLM API call.",
        operator_action_required=True,
    )
    status = err.to_status()
    assert status["runtime_status"] == "unavailable"
    assert status["attempted_runtime"] == "llm_api"
    assert status["provider"] == "qwen"
    assert status["reason"] == "missing_token"
    assert status["operator_action_required"] is True
    assert "safe_message" in status


def test_unavailable_error_str_does_not_expose_token():
    token = "sk-super-secret-token-12345"
    err = GPMRuntimeUnavailableError(
        reason="missing_token",
        attempted_runtime="llm_api",
        safe_message="LLM API unavailable: GPM_LLM_API_KEY is missing. Skipping LLM API call.",
    )
    assert token not in str(err)
    assert token not in err.safe_message
    assert token not in err.reason


def test_unavailable_error_default_operator_action_required():
    err = GPMRuntimeUnavailableError(reason="missing_token", attempted_runtime="llm_api")
    assert err.operator_action_required is True


# ---------------------------------------------------------------------------
# Resolver: explicit llm_api mode error paths
# ---------------------------------------------------------------------------


def test_explicit_llm_api_missing_token_raises_unavailable():
    """Explicit llm_api mode with no token -> GPMRuntimeUnavailableError, not RuntimeError."""
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        runtime_profile="local",
        enable_llm_api=True,
        llm_api_key=None,
    )
    with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
        resolve_runtime(config)
    err = exc_info.value
    assert err.reason == "missing_token"
    assert "GPM_LLM_API_KEY" in err.safe_message


def test_explicit_llm_api_disabled_raises_unavailable():
    """Explicit llm_api mode with API disabled -> GPMRuntimeUnavailableError."""
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        runtime_profile="local",
        enable_llm_api=False,
        llm_api_key="sk-test",
    )
    with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
        resolve_runtime(config)
    err = exc_info.value
    assert err.reason == "api_disabled"
    assert "sk-test" not in err.safe_message


def test_mock_mode_never_raises_unavailable():
    """mock mode always returns a runtime, never raises GPMRuntimeUnavailableError."""
    config = QwenRuntimeConfig(runtime_mode="mock", runtime_profile="local")
    runtime = resolve_runtime(config)
    assert runtime.runtime_mode == "mock"


# ---------------------------------------------------------------------------
# Resolver: server hard-fail remediation message
# ---------------------------------------------------------------------------


def test_server_unavailable_status_has_remediation():
    """Hard-fail safe_message names both remediation paths for the operator."""
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="server",
        enable_llm_api=False,
        llm_api_key=None,
        enable_local_model_fallback=False,
    )
    with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
        resolve_runtime(config)
    msg = exc_info.value.safe_message
    assert "GPM_LLM_API_KEY" in msg
    assert "GPM_QWEN_MNN_MODEL_PATH" in msg


def test_server_unavailable_does_not_expose_token():
    token = "sk-operator-secret"
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="server",
        enable_llm_api=True,
        llm_api_key=token,
        enable_local_model_fallback=False,
    )

    from unittest.mock import patch

    with patch(
        "src.gpm.qwen.qwen_runtime_resolver.QwenLocalRuntime",
        side_effect=RuntimeError("provider init failed"),
    ):
        with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
            resolve_runtime(config)

    err = exc_info.value
    assert token not in err.safe_message
    assert token not in err.reason
    assert token not in str(err)


# ---------------------------------------------------------------------------
# Config: redacted() does not expose token
# ---------------------------------------------------------------------------


def test_redacted_config_does_not_expose_token():
    token = "sk-real-api-key-do-not-leak"
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        runtime_profile="server",
        llm_api_key=token,
    )
    redacted = config.redacted()
    assert token not in str(redacted)
    assert redacted["llm_api_key"] == "***REDACTED***"


def test_redacted_none_token_shows_none():
    config = QwenRuntimeConfig(runtime_mode="mock", llm_api_key=None)
    assert config.redacted()["llm_api_key"] is None


# ---------------------------------------------------------------------------
# MNN fallback: unavailable in test env (MNN package not installed)
# ---------------------------------------------------------------------------


def test_server_auto_with_local_fallback_raises_unavailable_when_mnn_missing():
    """When MNN is not installed, fallback also fails -> GPMRuntimeUnavailableError.

    MNN package is not present in the test environment, so QwenMNNRuntime raises
    RuntimeError at init. The resolver must catch it and hard-fail with
    GPMRuntimeUnavailableError, not silently return mock.
    """
    config = QwenRuntimeConfig(
        runtime_mode="auto",
        runtime_profile="server",
        enable_llm_api=False,
        llm_api_key=None,
        enable_local_model_fallback=True,
        mnn_model_path="/nonexistent/model.mnn",
    )
    with pytest.raises(GPMRuntimeUnavailableError) as exc_info:
        resolve_runtime(config)
    err = exc_info.value
    assert err.operator_action_required is True
    assert "GPM_LLM_API_KEY" in err.safe_message
