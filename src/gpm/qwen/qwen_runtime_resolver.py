from __future__ import annotations

import dataclasses

from src.gpm.qwen.gpm_runtime_unavailable_error import GPMRuntimeUnavailableError
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig


def resolve_runtime(config: QwenRuntimeConfig):
    """Resolve a concrete runtime from config.

    Routing:
      mock / mnn            → direct, no fallback logic.
      llm_api               → operator API; RuntimeError → GPMRuntimeUnavailableError.
      auto + lightweight    → local-first (MNN → API if operator allows → hard fail).
      auto + server         → local-first with private context (same resolution order).
      auto + local / ci     → mock (CI-safe, no network required).

    Token is never included in error messages.
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
    if config.runtime_profile in ("lightweight", "server"):
        return _resolve_local_first(config)

    # local/ci + auto → mock (CI-safe, no network)
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


def _resolve_local_first(config: QwenRuntimeConfig):
    """Local-first resolution for lightweight and server profiles.

    Priority: local MNN model → LLM API (operator opt-in only) → hard fail.
    LLM API is never called unless enable_llm_api=True and a token is set.
    Never falls back to mock. Token never in any error message.
    """
    from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime

    last_reason = "no_runtime_configured"

    # Step 1: local MNN model (preferred; no network required)
    if config.mnn_model_path:
        mnn_config = dataclasses.replace(config, runtime_mode="mnn")
        try:
            return QwenLocalRuntime(config=mnn_config)
        except RuntimeError:
            last_reason = "local_model_unavailable"

    # Step 2: LLM API — only if operator explicitly enables it with a token
    if config.enable_llm_api:
        if config.llm_api_key:
            api_config = dataclasses.replace(config, runtime_mode="llm_api")
            try:
                return QwenLocalRuntime(config=api_config)
            except RuntimeError:
                last_reason = "provider_error"
        else:
            last_reason = "missing_token"
    elif config.llm_api_key:
        # Token provided but API flag not set by operator
        last_reason = "api_disabled"

    # Step 3: hard fail — operator must configure at least one callable runtime
    remediation = (
        "No callable GPM LLM runtime is available. "
        "Configure a local model via GPM_QWEN_MNN_MODEL_PATH, "
        "or provide GPM_LLM_API_KEY and set GPM_ENABLE_LLM_API=true."
    )
    raise GPMRuntimeUnavailableError(
        reason=last_reason,
        attempted_runtime="mnn,llm_api",
        provider=config.llm_provider,
        safe_message=remediation,
        operator_action_required=True,
    )
