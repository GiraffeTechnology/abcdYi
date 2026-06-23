from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class QwenRuntimeConfig:
    """Immutable runtime configuration for all Qwen runtime modes.

    Three controlled modes: mock (default, CI-safe), mnn (local model, no network),
    llm_api (operator-selected, disabled by default, requires explicit token).
    """

    runtime_mode: Literal["mock", "mnn", "llm_api"] = "mock"
    mnn_model_path: str | None = None
    mnn_tokenizer_path: str | None = None
    mnn_backend: str = "cpu"
    enable_live_mnn_tests: bool = False
    enable_llm_api: bool = False
    qwen_api_key: str | None = None
    qwen_api_base_url: str | None = None
    qwen_api_model: str | None = None
    llm_provider: str = "qwen"
    api_timeout_seconds: int = 60

    @classmethod
    def from_env(cls) -> "QwenRuntimeConfig":
        """Build config from environment variables. Default mode is mock."""
        raw_mode = os.environ.get("GPM_QWEN_RUNTIME_MODE", "mock").lower().strip()
        if raw_mode not in ("mock", "mnn", "llm_api"):
            raw_mode = "mock"

        # Prefer QWEN_API_KEY; fall back to DASHSCOPE_API_KEY. Never print either.
        api_key = (
            os.environ.get("QWEN_API_KEY", "").strip()
            or os.environ.get("DASHSCOPE_API_KEY", "").strip()
            or None
        )

        try:
            timeout = int(os.environ.get("GPM_QWEN_API_TIMEOUT_SECONDS", "60") or "60")
        except ValueError:
            timeout = 60

        return cls(
            runtime_mode=raw_mode,  # type: ignore[arg-type]
            mnn_model_path=os.environ.get("GPM_QWEN_MNN_MODEL_PATH", "").strip() or None,
            mnn_tokenizer_path=os.environ.get("GPM_QWEN_MNN_TOKENIZER_PATH", "").strip() or None,
            mnn_backend=os.environ.get("GPM_QWEN_MNN_BACKEND", "cpu").strip() or "cpu",
            enable_live_mnn_tests=os.environ.get(
                "GPM_ENABLE_LIVE_QWEN_MNN_TESTS", ""
            ).lower() in ("1", "true", "yes"),
            enable_llm_api=os.environ.get(
                "GPM_ENABLE_QWEN_LLM_API", ""
            ).lower() in ("1", "true", "yes"),
            qwen_api_key=api_key,
            qwen_api_base_url=os.environ.get("QWEN_API_BASE_URL", "").strip() or None,
            qwen_api_model=os.environ.get("QWEN_API_MODEL", "").strip() or None,
            llm_provider=os.environ.get("GPM_LLM_PROVIDER", "qwen").strip() or "qwen",
            api_timeout_seconds=timeout,
        )

    def redacted(self) -> dict:
        """Return a loggable dict — API key replaced with ***REDACTED***."""
        return {
            "runtime_mode": self.runtime_mode,
            "mnn_model_path": self.mnn_model_path,
            "mnn_backend": self.mnn_backend,
            "enable_live_mnn_tests": self.enable_live_mnn_tests,
            "enable_llm_api": self.enable_llm_api,
            "llm_api_key": "***REDACTED***" if self.qwen_api_key else None,
            "qwen_api_base_url": self.qwen_api_base_url,
            "qwen_api_model": self.qwen_api_model,
            "llm_provider": self.llm_provider,
            "api_timeout_seconds": self.api_timeout_seconds,
        }
