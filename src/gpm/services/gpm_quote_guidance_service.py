from __future__ import annotations

from typing import Any

from src.gpm.llm_adapters.local_llm_adapter import LocalLLMAdapter
from src.gpm.models.benchmark_snapshot import GPMBenchmarkSnapshot
from src.gpm.models.quote_guidance import GPMQuoteGuidance
from src.gpm.models.semantic_normalization import GPMSemanticNormalization
from src.gpm.pricing.benchmark_engine import BenchmarkEngine
from src.gpm.pricing.quote_guidance_engine import QuoteGuidanceEngine
from src.gpm.reports.markdown_report_builder import GPMMarkdownReportBuilder


class GPMQuoteGuidanceService:
    """Orchestrates the full GPM pricing intelligence pipeline."""

    def __init__(self, llm_adapter: LocalLLMAdapter) -> None:
        self._adapter = llm_adapter
        self._benchmark_engine = BenchmarkEngine()
        self._guidance_engine = QuoteGuidanceEngine()
        self._report_builder = GPMMarkdownReportBuilder()

    def run(
        self,
        requirement: dict,
        samples: list[Any],
        supplier_quote: dict,
        margin_policy: dict | None = None,
    ) -> tuple[GPMBenchmarkSnapshot, GPMQuoteGuidance, str]:
        normalizations: list[GPMSemanticNormalization] = []
        for sample in samples:
            raw = self._adapter.normalize_price_sample(requirement, sample)
            sid = sample.id if hasattr(sample, "id") else sample.get("id", "")
            from decimal import Decimal
            norm = GPMSemanticNormalization(
                sample_id=str(sid),
                is_comparable=raw["is_comparable"],
                comparability_score=Decimal(str(raw["comparability_score"])),
                reason=raw["reason"],
                normalized_product_type=raw.get("normalized_product_type"),
                normalized_material=raw.get("normalized_material"),
                normalized_process_tags=raw.get("normalized_process_tags", []),
                customization_supported=raw.get("customization_supported"),
            )
            normalizations.append(norm)

        benchmark = self._benchmark_engine.build_benchmark(requirement, samples, normalizations)
        guidance = self._guidance_engine.generate_guidance(
            requirement, supplier_quote, benchmark, margin_policy
        )
        report = self._report_builder.build_quote_guidance_report(guidance, benchmark)
        return benchmark, guidance, report
