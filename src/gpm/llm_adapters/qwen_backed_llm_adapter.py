from __future__ import annotations

from typing import Any

from .local_llm_adapter import LocalLLMAdapter


class QwenBackedLLMAdapter(LocalLLMAdapter):
    """LocalLLMAdapter backed by a QwenRuntime.

    Bridges Session C QwenRuntime into the Session B normalize_price_sample pipeline.
    Builds a per-sample context bundle and calls the runtime for each sample.
    """

    def __init__(self, qwen_runtime: Any) -> None:
        self._runtime = qwen_runtime

    def normalize_price_sample(self, requirement: dict, sample: Any) -> dict:
        from src.gpm.context.in_memory_context_retriever import InMemoryGPMContextRetriever
        from src.gpm.prompts.qwen_semantic_analysis_prompt import (
            build_qwen_semantic_analysis_prompt,
        )

        retriever = InMemoryGPMContextRetriever(price_samples=[sample])
        context = retriever.build_context(
            requirement=requirement,
            data_mode="mock",
        )
        prompt = build_qwen_semantic_analysis_prompt(context)
        output = self._runtime.generate_json(
            prompt, schema_name="qwen_semantic_analysis"
        )
        return {
            "is_comparable": output.get("is_comparable", False),
            "comparability_score": output.get("comparability_score", 0.0),
            "normalized_product_type": output.get("normalized_product_type"),
            "normalized_material": output.get("normalized_material"),
            "normalized_process_tags": output.get("normalized_process_tags", []),
            "customization_supported": None,
            "reason": output.get("reason", ""),
        }
