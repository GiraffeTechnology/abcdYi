"""Tests for QwenLocalRuntime mode selection and guard behavior."""
from __future__ import annotations

import pytest

from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
from src.gpm.qwen.mock_qwen_runtime import MockQwenRuntime
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig


def test_qwen_local_runtime_selects_mock_by_default() -> None:
    runtime = QwenLocalRuntime(config=QwenRuntimeConfig(runtime_mode="mock"))
    assert runtime.runtime_mode == "mock"
    assert isinstance(runtime._runtime, MockQwenRuntime)


def test_qwen_local_runtime_mock_mode_legacy_kwarg() -> None:
    """Legacy callers using mock_mode=True must still work."""
    runtime = QwenLocalRuntime(mock_mode=True)
    assert runtime.runtime_mode == "mock"


def test_qwen_local_runtime_selects_mnn_raises_without_model() -> None:
    config = QwenRuntimeConfig(runtime_mode="mnn", mnn_model_path=None)
    with pytest.raises(RuntimeError, match="GPM_QWEN_MNN_MODEL_PATH"):
        QwenLocalRuntime(config=config)


def test_qwen_local_runtime_selects_mnn_raises_missing_file(tmp_path: pytest.TempPathFactory) -> None:
    config = QwenRuntimeConfig(runtime_mode="mnn", mnn_model_path="/nonexistent/model.mnn")
    with pytest.raises(RuntimeError):
        QwenLocalRuntime(config=config)


def test_qwen_local_runtime_selects_llm_api_only_when_enabled() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        qwen_api_key="sk-test-token",
    )
    # Raises not on init of QwenLocalRuntime but on OperatorLLMApiRuntime construction.
    # With valid config, it should succeed (no network call at init).
    runtime = QwenLocalRuntime(config=config)
    assert runtime.runtime_mode == "llm_api"


def test_qwen_local_runtime_llm_api_raises_when_disabled() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=False,
        qwen_api_key="sk-test-token",
    )
    with pytest.raises(RuntimeError, match="disabled"):
        QwenLocalRuntime(config=config)


def test_qwen_local_runtime_does_not_auto_fallback_to_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock mode must not silently switch to LLM API even if env vars are set."""
    monkeypatch.setenv("GPM_ENABLE_QWEN_LLM_API", "true")
    monkeypatch.setenv("QWEN_API_KEY", "sk-something")
    # Explicit mock config overrides env
    runtime = QwenLocalRuntime(config=QwenRuntimeConfig(runtime_mode="mock"))
    assert runtime.runtime_mode == "mock"


def test_generate_json_mock_returns_dict() -> None:
    runtime = QwenLocalRuntime(config=QwenRuntimeConfig(runtime_mode="mock"))
    result = runtime.generate_json("men cotton shirt OEM\nev_ms-001", schema_name="gpm")
    assert isinstance(result, dict)
    assert result.get("human_approval_required") is True
