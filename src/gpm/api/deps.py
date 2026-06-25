from __future__ import annotations

from functools import lru_cache

from fastapi import HTTPException

from src.gpm.context.retrievers.retriever_config import build_context_retriever_from_env
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
from src.gpm.services.gpm_quote_guidance_api_service import GPMQuoteGuidanceApiService


@lru_cache(maxsize=1)
def get_runtime_config() -> QwenRuntimeConfig:
    return QwenRuntimeConfig.from_env()


@lru_cache(maxsize=1)
def _try_build_service() -> tuple[GPMQuoteGuidanceApiService | None, str | None]:
    """Build the GPM service once, capturing init errors for structured responses.

    Returns (service, None) on success, or (None, error_str) on RuntimeError
    (e.g. giraffe_db mode with missing base URL). Result is cached so
    misconfiguration is not re-evaluated on every request.
    """
    try:
        runtime_config = get_runtime_config()
        context_retriever = build_context_retriever_from_env()
        return GPMQuoteGuidanceApiService(
            runtime_config=runtime_config,
            context_retriever=context_retriever,
        ), None
    except RuntimeError as exc:
        return None, str(exc)


def get_quote_guidance_service() -> GPMQuoteGuidanceApiService:
    """FastAPI dependency — returns the service or raises a structured 502."""
    svc, err = _try_build_service()
    if err is not None:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "context_unavailable",
                "error": err,
                "operator_action_required": True,
            },
        )
    return svc  # type: ignore[return-value]
