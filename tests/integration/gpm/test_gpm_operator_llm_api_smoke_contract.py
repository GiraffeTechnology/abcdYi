"""Contract tests for OperatorLLMApiRuntime: verify guard behavior without network calls."""
from __future__ import annotations

import pytest

from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
from src.gpm.qwen.operator_llm_api_runtime import OperatorLLMApiRuntime, LLMApiProvider
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig


def test_operator_runtime_is_default_off() -> None:
    """Default config must not enable LLM API."""
    config = QwenRuntimeConfig()
    assert config.enable_llm_api is False


def test_operator_runtime_raises_when_disabled() -> None:
    config = QwenRuntimeConfig(runtime_mode="llm_api", enable_llm_api=False, llm_api_key="sk-x")
    with pytest.raises(RuntimeError, match="disabled"):
        OperatorLLMApiRuntime(config)


def test_operator_runtime_raises_without_token() -> None:
    config = QwenRuntimeConfig(runtime_mode="llm_api", enable_llm_api=True, llm_api_key=None)
    with pytest.raises(RuntimeError, match="GPM_LLM_API_KEY"):
        OperatorLLMApiRuntime(config)


def test_operator_runtime_constructs_with_valid_config() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        llm_api_key="sk-test",
        llm_provider="qwen",
    )
    runtime = OperatorLLMApiRuntime(config)
    assert runtime.runtime_mode == "llm_api"
    assert runtime.provider_name == "qwen"


def test_openai_compatible_provider_constructs() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        llm_api_key="sk-oc",
        llm_provider="openai_compatible",
    )
    runtime = OperatorLLMApiRuntime(config)
    assert runtime.provider_name == "openai_compatible"


def test_custom_http_provider_requires_base_url() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        llm_api_key="sk-ch",
        llm_provider="custom_http",
        llm_api_base_url=None,
    )
    with pytest.raises(RuntimeError, match="GPM_LLM_API_BASE_URL"):
        OperatorLLMApiRuntime(config)


def test_custom_http_provider_constructs_with_url() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        llm_api_key="sk-ch",
        llm_provider="custom_http",
        llm_api_base_url="https://my-llm.internal/api",
    )
    runtime = OperatorLLMApiRuntime(config)
    assert runtime.provider_name == "custom_http"


def test_provider_satisfies_protocol() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        llm_api_key="sk-test",
        llm_provider="qwen",
    )
    runtime = OperatorLLMApiRuntime(config)
    assert isinstance(runtime._provider, LLMApiProvider)


def test_local_runtime_with_llm_api_mode_constructs() -> None:
    config = QwenRuntimeConfig(
        runtime_mode="llm_api",
        enable_llm_api=True,
        llm_api_key="sk-test",
    )
    wrapper = QwenLocalRuntime(config=config)
    assert wrapper.runtime_mode == "llm_api"
