from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
from src.gpm.models.qwen_semantic_analysis import QwenSemanticAnalysis
from src.gpm.models.semantic_normalization import GPMSemanticNormalization
from src.gpm.pricing.benchmark_engine import BenchmarkEngine
from src.gpm.pricing.quote_guidance_engine import QuoteGuidanceEngine
from src.gpm.prompts.qwen_gpm_normalization_prompt import build_qwen_gpm_normalization_prompt
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
from src.gpm.validators.context_bundle_validator import ContextBundleValidator
from src.gpm.validators.qwen_output_validator import QwenOutputValidator


class GPMSemanticQuoteService:
    """Session D/E main service: context bundle + Qwen semantic analysis + benchmark guidance.

    Flow:
        ContextRetriever -> GPMContextBundle
        -> ContextBundleValidator
        -> Prompt builder
        -> QwenLocalRuntime (mock | mnn | llm_api | auto)
        -> QwenOutputValidator
        -> BenchmarkEngine + QuoteGuidanceEngine
        -> final semantic quote packet with human_approval_required: True
    """

    def __init__(
        self,
        retriever: Any = None,
        runtime: QwenLocalRuntime | None = None,
        context_retriever: Any = None,
        qwen_runtime: QwenLocalRuntime | None = None,
    ) -> None:
        # Accept both old (retriever/runtime) and new (context_retriever/qwen_runtime) param names.
        _ret = context_retriever if context_retriever is not None else retriever
        if _ret is None:
            from src.gpm.context.retrievers.retriever_config import build_context_retriever_from_env
            _ret = build_context_retriever_from_env()
        self._retriever = _ret
        self._runtime = qwen_runtime if qwen_runtime is not None else runtime

    def run(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        rfq_id: str | None = None,
        supplier_response_id: str | None = None,
        include_private_data: bool | None = None,
        runtime_mode: Literal["mock", "mnn", "llm_api", "auto"] | None = None,
        evidence_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        runtime = self._resolve_runtime(runtime_mode)

        bundle: GPMContextBundle = self._retriever.retrieve(
            tenant_id=tenant_id,
            project_id=project_id,
            rfq_id=rfq_id,
            supplier_response_id=supplier_response_id,
            include_private_data=include_private_data,
            evidence_ids=evidence_ids,
        )

        ContextBundleValidator().validate(bundle)

        prompt = build_qwen_gpm_normalization_prompt(bundle)
        raw_qwen_output = runtime.generate_json(prompt, schema_name="gpm_normalization")

        QwenOutputValidator().validate(raw_qwen_output, bundle)

        analysis = QwenSemanticAnalysis(**raw_qwen_output)

        price_samples = bundle.price_samples
        normalizations = [
            GPMSemanticNormalization(
                sample_id=str(
                    s.get("id") if isinstance(s, dict) else getattr(s, "id", "")
                ),
                is_comparable=analysis.is_comparable,
                comparability_score=Decimal(str(analysis.comparability_score)),
                normalized_product_type=analysis.normalized_product_type,
                normalized_material=analysis.normalized_material,
                normalized_process_tags=analysis.normalized_process_tags,
                customization_supported=None,
                reason=analysis.reason,
            )
            for s in price_samples
        ]

        requirement = bundle.requirement
        supplier_quote = bundle.supplier_quote or {}

        benchmark = BenchmarkEngine().build_benchmark(requirement, price_samples, normalizations)
        guidance = QuoteGuidanceEngine().generate_guidance(requirement, supplier_quote, benchmark)

        return {
            "context_bundle_id": bundle.bundle_id,
            "runtime_mode": runtime.runtime_mode,
            "semantic_analysis": {
                "normalized_product_type": analysis.normalized_product_type,
                "normalized_material": analysis.normalized_material,
                "normalized_process_tags": analysis.normalized_process_tags,
                "is_comparable": analysis.is_comparable,
                "comparability_score": analysis.comparability_score,
                "detected_mismatch_flags": analysis.detected_mismatch_flags,
                "missing_fields": analysis.missing_fields,
                "risk_explanation": analysis.risk_explanation,
                "evidence_ids": analysis.evidence_ids,
                "reason": analysis.reason,
                "confidence": analysis.confidence,
            },
            "benchmark_snapshot": {
                "confidence": benchmark.confidence_level,
                "comparable_sample_count": benchmark.comparable_sample_count,
            },
            "quote_guidance": {
                "supplier_quote_position": guidance.supplier_quote_position,
                "accept_recommendation": guidance.accept_recommendation,
            },
            "supplier_quote_position": guidance.supplier_quote_position,
            "accept_recommendation": guidance.accept_recommendation,
            "human_approval_required": True,
            "evidence_ids": analysis.evidence_ids,
            "risk_flags": analysis.detected_mismatch_flags,
            "explanation": analysis.reason,
        }

    def _resolve_runtime(
        self, runtime_mode: Literal["mock", "mnn", "llm_api", "auto"] | None
    ) -> QwenLocalRuntime:
        from src.gpm.qwen.qwen_runtime_resolver import resolve_runtime

        if self._runtime is not None:
            return self._runtime

        if runtime_mode is not None:
            import dataclasses
            env_config = QwenRuntimeConfig.from_env()
            config = dataclasses.replace(env_config, runtime_mode=runtime_mode)
        else:
            config = QwenRuntimeConfig.from_env()

        return resolve_runtime(config)
