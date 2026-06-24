from __future__ import annotations

import dataclasses

from src.gpm.qwen.gpm_runtime_unavailable_error import GPMRuntimeUnavailableError
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig


def resolve_runtime(config: QwenRuntimeConfig):
    """Resolve a concrete runtime, applying server-profile API-first logic.

    Returns QwenLocalRuntime for concrete modes, or raises GPMRuntimeUnavailableError
    when no callable runtime exists. Token is never included in error messages.
    """
    from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime

    mode = config.runtime_mode

    if mode == "mock":
        return QwenLocalRuntime(config=config)
    if mode == "mnn":
        return QwenLocalRuntime(config=config)
    if mode == "llm_api":
        return _try_llm_api(config)

    # auto: profile determines resolution strategy
    if config.runtime_profile == "server":
        return _resolve_server_auto(config)

    # local/ci + auto → safe mock default (CI-safe, no network)
    return QwenLocalRuntime(config=dataclasses.replace(config, runtime_mode="mock"))


def _try_llm_api(config: QwenRuntimeConfig):
    """Attempt OperatorLLMApiRuntime; convert RuntimeError to GPMRuntimeUnavailableError."""
    from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime

    api_config = dataclasses.replace(config, runtime_mode="llm_api")
    try:
        return QwenLocalRuntime(config=api_config)
    except RuntimeError as exc:
        msg = str(exc)
        if "GPM_LLM_API_KEY" in msg:
            raise GPMRuntimeUnavailableError(
                reason="missing_token",
                attempted_runtime="llm_api",
                provider=config.llm_provider,
                safe_message=(
                    "LLM API unavailable: GPM_LLM_API_KEY is missing. "
                    "Skipping LLM API call."
                ),
            ) from None
        if "disabled" in msg.lower():
            raise GPMRuntimeUnavailableError(
                reason="api_disabled",
                attempted_runtime="llm_api",
                provider=config.llm_provider,
                safe_message=(
                    "LLM API unavailable: LLM API mode is disabled. "
                    "Set GPM_ENABLE_LLM_API=true. Skipping LLM API call."
                ),
            ) from None
        raise GPMRuntimeUnavailableError(
            reason="provider_error",
            attempted_runtime="llm_api",
            provider=config.llm_provider,
            safe_message="LLM API unavailable: provider init failed. Skipping LLM API call.",
        ) from None


def _resolve_server_auto(config: QwenRuntimeConfig):
    """Server-profile auto-resolution: API-first, optional MNN fallback, hard fail.

    Never silently falls back to mock. Token is never included in any message.
    """
    from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime

    unavailable_reason: str
    unavailable_message: str

    # Step 1: attempt LLM API
    if config.enable_llm_api and config.llm_api_key:
        api_config = dataclasses.replace(config, runtime_mode="llm_api")
        try:
            return QwenLocalRuntime(config=api_config)
        except RuntimeError:
            unavailable_reason = "provider_error"
            unavailable_message = (
                "LLM API unavailable: provider init failed. Skipping LLM API call."
            )
    elif not config.llm_api_key:
        unavailable_reason = "missing_token"
        unavailable_message = (
            "LLM API unavailable: GPM_LLM_API_KEY is missing. Skipping LLM API call."
        )
    else:
        unavailable_reason = "api_disabled"
        unavailable_message = (
            "LLM API unavailable: LLM API mode is disabled. "
            "Set GPM_ENABLE_LLM_API=true. Skipping LLM API call."
        )

    # Step 2: optional local model fallback (must be explicitly enabled)
    if config.enable_local_model_fallback and config.mnn_model_path:
        mnn_config = dataclasses.replace(config, runtime_mode="mnn")
        try:
            return QwenLocalRuntime(config=mnn_config)
        except RuntimeError:
            pass  # MNN also unavailable; fall through to hard fail

    # Step 3: hard fail — no callable runtime for server mode
    remediation = (
        "No callable GPM LLM runtime is available for server mode. "
        "Provide a valid operator LLM API token via GPM_LLM_API_KEY "
        "or configure a local model path via GPM_QWEN_MNN_MODEL_PATH "
        "and set GPM_ENABLE_LOCAL_MODEL_FALLBACK=true."
    )
    raise GPMRuntimeUnavailableError(
        reason=unavailable_reason,
        attempted_runtime="llm_api",
        provider=config.llm_provider,
        safe_message=remediation,
        operator_action_required=True,
    )
