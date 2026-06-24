from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class QwenRuntimeConfig:
    """Immutable runtime configuration for all GPM runtime modes.

    Modes: mock (default, CI-safe), mnn (local model, no network),
    llm_api (operator-selected, disabled by default, requires explicit token),
    auto (resolved by runtime_profile: server→API-first, others→mock).

    Profiles: local (default), ci, server.
    Server profile defaults runtime_mode to "auto" and applies API-first resolution.

    Canonical env vars take priority over Qwen-specific aliases in from_env().
    """

    runtime_mode: Literal["mock", "mnn", "llm_api", "auto"] = "mock"
    runtime_profile: Literal["local", "ci", "server"] = "local"
    mnn_model_path: str | None = None
    mnn_tokenizer_path: str | None = None
    mnn_backend: str = "cpu"
    enable_live_mnn_tests: bool = False
    enable_llm_api: bool = False
    enable_local_model_fallback: bool = False
    llm_api_key: str | None = None       # canonical; Qwen aliases: QWEN_API_KEY, DASHSCOPE_API_KEY
    llm_api_base_url: str | None = None  # canonical; Qwen alias: QWEN_API_BASE_URL
    llm_api_model: str | None = None     # canonical; Qwen alias: QWEN_API_MODEL
    llm_provider: str = "qwen"
    api_timeout_seconds: int = 60

    @classmethod
    def from_env(cls) -> "QwenRuntimeConfig":
        """Build config from environment variables.

        Canonical env vars take priority over Qwen-specific aliases:
          GPM_RUNTIME_PROFILE         (local|ci|server; default local)
          GPM_LLM_RUNTIME_MODE        > GPM_QWEN_RUNTIME_MODE
          GPM_ENABLE_LLM_API          > GPM_ENABLE_QWEN_LLM_API
          GPM_LLM_API_KEY             > QWEN_API_KEY > DASHSCOPE_API_KEY
          GPM_LLM_API_BASE_URL        > QWEN_API_BASE_URL
          GPM_LLM_API_MODEL           > QWEN_API_MODEL
          GPM_LLM_API_TIMEOUT_SECONDS > GPM_QWEN_API_TIMEOUT_SECONDS
          GPM_ENABLE_LOCAL_MODEL_FALLBACK (false by default)
        """
        profile_raw = os.environ.get("GPM_RUNTIME_PROFILE", "local").lower().strip()
        if profile_raw not in ("local", "ci", "server"):
            profile_raw = "local"

        explicit_mode = (
            os.environ.get("GPM_LLM_RUNTIME_MODE", "").lower().strip()
            or os.environ.get("GPM_QWEN_RUNTIME_MODE", "").lower().strip()
            or ""
        )
        if explicit_mode not in ("mock", "mnn", "llm_api", "auto"):
            explicit_mode = ""

        # Server profile defaults to "auto" (API-first); others default to "mock".
        raw_mode = explicit_mode or ("auto" if profile_raw == "server" else "mock")

        # GPM_LLM_API_KEY > QWEN_API_KEY > DASHSCOPE_API_KEY. Never print any of these.
        api_key = (
            os.environ.get("GPM_LLM_API_KEY", "").strip()
            or os.environ.get("QWEN_API_KEY", "").strip()
            or os.environ.get("DASHSCOPE_API_KEY", "").strip()
            or None
        )

        enable_llm_api_str = (
            os.environ.get("GPM_ENABLE_LLM_API", "").lower().strip()
            or os.environ.get("GPM_ENABLE_QWEN_LLM_API", "").lower().strip()
        )
        enable_llm_api = enable_llm_api_str in ("1", "true", "yes")

        enable_fallback_str = os.environ.get("GPM_ENABLE_LOCAL_MODEL_FALLBACK", "").lower().strip()
        enable_local_model_fallback = enable_fallback_str in ("1", "true", "yes")

        api_base_url = (
            os.environ.get("GPM_LLM_API_BASE_URL", "").strip()
            or os.environ.get("QWEN_API_BASE_URL", "").strip()
            or None
        )

        api_model = (
            os.environ.get("GPM_LLM_API_MODEL", "").strip()
            or os.environ.get("QWEN_API_MODEL", "").strip()
            or None
        )

        timeout_str = (
            os.environ.get("GPM_LLM_API_TIMEOUT_SECONDS", "").strip()
            or os.environ.get("GPM_QWEN_API_TIMEOUT_SECONDS", "").strip()
            or "60"
        )
        try:
            timeout = int(timeout_str)
        except ValueError:
            timeout = 60

        return cls(
            runtime_mode=raw_mode,  # type: ignore[arg-type]
            runtime_profile=profile_raw,  # type: ignore[arg-type]
            mnn_model_path=os.environ.get("GPM_QWEN_MNN_MODEL_PATH", "").strip() or None,
            mnn_tokenizer_path=os.environ.get("GPM_QWEN_MNN_TOKENIZER_PATH", "").strip() or None,
            mnn_backend=os.environ.get("GPM_QWEN_MNN_BACKEND", "cpu").strip() or "cpu",
            enable_live_mnn_tests=os.environ.get(
                "GPM_ENABLE_LIVE_QWEN_MNN_TESTS", ""
            ).lower() in ("1", "true", "yes"),
            enable_llm_api=enable_llm_api,
            enable_local_model_fallback=enable_local_model_fallback,
            llm_api_key=api_key,
            llm_api_base_url=api_base_url,
            llm_api_model=api_model,
            llm_provider=os.environ.get("GPM_LLM_PROVIDER", "qwen").strip() or "qwen",
            api_timeout_seconds=timeout,
        )

    def redacted(self) -> dict:
        """Return a loggable dict — API key replaced with ***REDACTED***."""
        return {
            "runtime_mode": self.runtime_mode,
            "runtime_profile": self.runtime_profile,
            "enable_local_model_fallback": self.enable_local_model_fallback,
            "mnn_model_path": self.mnn_model_path,
            "mnn_backend": self.mnn_backend,
            "enable_live_mnn_tests": self.enable_live_mnn_tests,
            "enable_llm_api": self.enable_llm_api,
            "llm_api_key": "***REDACTED***" if self.llm_api_key else None,
            "llm_api_base_url": self.llm_api_base_url,
            "llm_api_model": self.llm_api_model,
            "llm_provider": self.llm_provider,
            "api_timeout_seconds": self.api_timeout_seconds,
        }
