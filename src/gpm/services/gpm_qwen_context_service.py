from __future__ import annotations

from decimal import Decimal
from typing import Any

from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.models.qwen_semantic_analysis import QwenSemanticAnalysis
from src.gpm.models.semantic_normalization import GPMSemanticNormalization
from src.gpm.pricing.benchmark_engine import BenchmarkEngine
from src.gpm.pricing.quote_guidance_engine import QuoteGuidanceEngine
from src.gpm.prompts.qwen_gpm_normalization_prompt import build_qwen_gpm_normalization_prompt
from src.gpm.validators.context_bundle_validator import ContextBundleValidator
from src.gpm.validators.qwen_output_validator import GPMServiceOutputValidator, QwenOutputValidator


class GPMQwenContextService:
    """Combines GPM context retrieval, local Qwen semantic analysis, and Session B benchmark engines.

    Flow:
        ContextRetriever → GPMContextBundle
        → Qwen normalization prompt
        → QwenLocalRuntime.generate_json()
        → QwenOutputValidator
        → Session B BenchmarkEngine + QuoteGuidanceEngine
        → GPMServiceOutputValidator
        → combined output dict
    """

    def __init__(self, retriever: Any, runtime: Any) -> None:
        self._retriever = retriever
        self._runtime = runtime

    def run(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        rfq_id: str | None = None,
        supplier_response_id: str | None = None,
        include_private_data: bool = False,
    ) -> dict[str, Any]:
        bundle: GPMContextBundle = self._retriever.build_gpm_context(
            tenant_id=tenant_id,
            project_id=project_id,
            rfq_id=rfq_id,
            supplier_response_id=supplier_response_id,
            include_private_data=include_private_data,
        )

        ContextBundleValidator().validate(bundle)

        prompt = build_qwen_gpm_normalization_prompt(bundle)
        raw_qwen_output = self._runtime.generate_json(prompt, schema_name="gpm_normalization")

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

        combined: dict[str, Any] = {
            **raw_qwen_output,
            "supplier_quote_position": guidance.supplier_quote_position,
            "accept_recommendation": guidance.accept_recommendation,
            "human_approval_required": guidance.human_approval_required,
            "benchmark_confidence": benchmark.confidence_level,
            "benchmark_comparable_samples": benchmark.comparable_sample_count,
        }

        GPMServiceOutputValidator().validate(combined, bundle)

        return combined
