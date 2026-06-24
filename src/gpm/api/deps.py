from __future__ import annotations

from functools import lru_cache

from src.gpm.context.retrievers.retriever_config import build_context_retriever_from_env
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
from src.gpm.services.gpm_quote_guidance_api_service import GPMQuoteGuidanceApiService


@lru_cache(maxsize=1)
def get_runtime_config() -> QwenRuntimeConfig:
    return QwenRuntimeConfig.from_env()


@lru_cache(maxsize=1)
def get_quote_guidance_service() -> GPMQuoteGuidanceApiService:
    runtime_config = get_runtime_config()
    context_retriever = build_context_retriever_from_env()
    return GPMQuoteGuidanceApiService(
        runtime_config=runtime_config,
        context_retriever=context_retriever,
    )
