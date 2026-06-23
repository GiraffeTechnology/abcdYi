"""Integration test: Session A samples → context bundle → mock Qwen → validator → Session B engines."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.gpm.context.in_memory_context_retriever import InMemoryGPMContextRetriever
from src.gpm.llm_adapters.mock_llm_adapter import MockLLMAdapter
from src.gpm.models.qwen_semantic_analysis import QwenSemanticAnalysis
from src.gpm.models.semantic_normalization import GPMSemanticNormalization
from src.gpm.pricing.benchmark_engine import BenchmarkEngine
from src.gpm.pricing.quote_guidance_engine import QuoteGuidanceEngine
from src.gpm.prompts.qwen_semantic_analysis_prompt import build_qwen_semantic_analysis_prompt
from src.gpm.qwen.mock_qwen_runtime import MockQwenRuntime
from src.gpm.validators.context_bundle_validator import ContextBundleValidator
from src.gpm.validators.qwen_output_validator import QwenOutputValidator


@dataclass
class _MockSample:
    id: str
    product_title: str
    price_min: Decimal
    price_max: Decimal
    price_currency: str = "CNY"
    price_unit: str = "piece"
    moq: Decimal = Decimal("1000")
    moq_unit: str = "piece"
    material: str = "100% cotton"
    source_platform: str = "mock_1688"
    usable_for_benchmark: bool = True
    invalid_reasons: list[str] = field(default_factory=list)
    ladder_prices: list[dict] = field(default_factory=list)
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


LADDER = [
    {"min_qty": 500, "price": 38},
    {"min_qty": 3000, "price": 32},
    {"min_qty": 10000, "price": 28},
]

SAMPLE_TITLES = [
    "men cotton shirt OEM custom",
    "100% cotton shirt men",
    "OEM cotton shirt men Japan export",
    "men shirt 100% cotton",
    "pure cotton shirt OEM custom Japan",
    "men cotton shirt wholesale",
    "100% cotton OEM shirt Japan",
    "men shirt cotton fabric OEM",
    "cotton shirt custom men",
    "men OEM cotton shirt Japan export",
    "cotton shirt men manufacturing",
    "men cotton shirt bulk order",
    "100% cotton shirt bulk",
    "OEM men shirt cotton fabric",
    "men shirt pure cotton OEM",
    "men cotton shirt custom order",
    "pure cotton OEM shirt",
    "men shirt cotton wholesale",
    "custom men shirt 100% cotton",
    "men cotton shirt factory OEM",
]

# Prices from 28 to 45.1 to ensure 38.5 CNY quote falls in within_high_range → negotiate
_SAMPLE_PRICES = [Decimal(str(round(28.0 + i * 0.9, 2))) for i in range(20)]

REQUIREMENT = {
    "id": "req-integration-001",
    "product": "men's cotton shirt",
    "quantity": 10000,
    "unit": "piece",
    "material": "100% cotton",
    "process_tags": ["cutting", "sewing", "buttoning", "packing"],
    "target_market": "Japan",
    "source_platform": "mock_1688",
}

SUPPLIER_QUOTE = {
    "supplier_id": "supplier_abc",
    "unit_price": 38.5,
    "currency": "CNY",
    "unit": "piece",
    "moq": 1000,
}


@pytest.fixture
def samples() -> list[_MockSample]:
    # No ladder prices: use varied price_min so benchmark range includes 38.5 CNY
    return [
        _MockSample(
            id=f"ms-{i+1:03d}",
            product_title=title,
            price_min=_SAMPLE_PRICES[i],
            price_max=_SAMPLE_PRICES[i] + Decimal("3"),
            ladder_prices=[],
        )
        for i, title in enumerate(SAMPLE_TITLES)
    ]


def test_full_context_flow_passes(samples: list[_MockSample]) -> None:
    """Full Session A → context → Qwen → validator → Session B pipeline."""
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    bundle = retriever.build_context(REQUIREMENT, SUPPLIER_QUOTE, data_mode="mock")

    ContextBundleValidator().validate(bundle)

    prompt = build_qwen_semantic_analysis_prompt(bundle)
    runtime = MockQwenRuntime()
    raw_output = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")

    QwenOutputValidator().validate(raw_output, bundle)

    analysis = QwenSemanticAnalysis(**raw_output)
    assert analysis.normalized_product_type == "men_cotton_shirt"
    assert analysis.normalized_material == "cotton"
    assert analysis.comparability_score == 0.85

    # Feed to Session B engines via MockLLMAdapter normalization
    llm = MockLLMAdapter()
    normalizations = []
    for s in samples:
        norm_dict = llm.normalize_price_sample(REQUIREMENT, s)
        normalizations.append(GPMSemanticNormalization(
            sample_id=s.id,
            is_comparable=norm_dict["is_comparable"],
            comparability_score=Decimal(str(norm_dict["comparability_score"])),
            normalized_product_type=norm_dict.get("normalized_product_type"),
            normalized_material=norm_dict.get("normalized_material"),
            normalized_process_tags=norm_dict.get("normalized_process_tags", []),
            customization_supported=norm_dict.get("customization_supported"),
            reason=norm_dict.get("reason", ""),
        ))

    benchmark = BenchmarkEngine().build_benchmark(REQUIREMENT, samples, normalizations)
    assert benchmark.confidence_level == "high"
    assert benchmark.comparable_sample_count >= 20

    guidance = QuoteGuidanceEngine().generate_guidance(REQUIREMENT, SUPPLIER_QUOTE, benchmark)
    assert guidance.human_approval_required is True
    assert guidance.supplier_quote_position in ("within_high_range", "within_mid_range", "above_market")
    assert guidance.accept_recommendation == "negotiate"


def test_no_external_llm_api_in_flow(samples: list[_MockSample]) -> None:
    """Verify no external API is called in the context flow."""
    import sys
    forbidden = ("openai", "anthropic", "dashscope", "google.generativeai", "deepseek")
    for mod in forbidden:
        assert mod not in sys.modules, f"Forbidden external LLM module {mod!r} was imported."


def test_human_approval_required_always_true(samples: list[_MockSample]) -> None:
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    bundle = retriever.build_context(REQUIREMENT, SUPPLIER_QUOTE, data_mode="mock")
    prompt = build_qwen_semantic_analysis_prompt(bundle)
    raw_output = MockQwenRuntime().generate_json(prompt, schema_name="qwen_semantic_analysis")
    QwenOutputValidator().validate(raw_output, bundle)

    llm = MockLLMAdapter()
    normalizations = [
        GPMSemanticNormalization(
            sample_id=s.id,
            **{k: (Decimal(str(v)) if k == "comparability_score" else v)
               for k, v in llm.normalize_price_sample(REQUIREMENT, s).items()
               if k in ("is_comparable", "comparability_score", "normalized_product_type",
                        "normalized_material", "normalized_process_tags", "customization_supported", "reason")}
        )
        for s in samples
    ]
    benchmark = BenchmarkEngine().build_benchmark(REQUIREMENT, samples, normalizations)
    guidance = QuoteGuidanceEngine().generate_guidance(REQUIREMENT, SUPPLIER_QUOTE, benchmark)
    assert guidance.human_approval_required is True


def test_qwen_output_evidence_ids_valid(samples: list[_MockSample]) -> None:
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    bundle = retriever.build_context(REQUIREMENT, SUPPLIER_QUOTE, data_mode="mock")
    prompt = build_qwen_semantic_analysis_prompt(bundle)
    raw_output = MockQwenRuntime().generate_json(prompt, schema_name="qwen_semantic_analysis")
    valid_ids = bundle.evidence_ids()
    for eid in raw_output.get("evidence_ids", []):
        assert eid in valid_ids, f"Invalid evidence_id cited: {eid}"
