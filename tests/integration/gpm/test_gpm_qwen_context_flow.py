from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample
from src.gpm.context.in_memory_context_retriever import InMemoryGPMContextRetriever
from src.gpm.qwen.mock_qwen_runtime import MockQwenRuntime
from src.gpm.prompts.qwen_semantic_analysis_prompt import build_qwen_semantic_analysis_prompt
from src.gpm.validators.qwen_output_validator import validate_qwen_output
from src.gpm.validators.context_bundle_validator import validate_context_bundle
from src.gpm.models.qwen_semantic_analysis import QwenSemanticAnalysis
from src.gpm.llm_adapters.mock_llm_adapter import MockLLMAdapter
from src.gpm.services.gpm_quote_guidance_service import GPMQuoteGuidanceService


def _make_shirt_sample(i: int) -> GPMSupplierPriceSample:
    p = 26 + (i % 20)
    sample = GPMSupplierPriceSample(
        id=f"sample_{i:03d}",
        source_platform="1688_mock",
        source_offer_id=f"offer_{i:03d}",
        supplier_id=f"sup_{i:03d}",
        supplier_name=f"Supplier {i}",
        supplier_location="Guangzhou",
        captured_at=datetime.now(timezone.utc),
        observed_at=datetime.now(timezone.utc),
        product_title="men cotton shirt OEM custom 定制纯棉衬衫",
        product_url=None,
        image_url=None,
        category_id="apparel",
        category_name="Men's Shirts",
        material="100% cotton",
        process_tags=["oem"],
        customization_supported=True,
        price_min=Decimal(str(p + 14)),
        price_max=Decimal(str(p + 22)),
        price_currency="CNY",
        price_unit="piece",
        moq=Decimal("1000"),
        moq_unit="piece",
        ladder_prices=[
            {"min_qty": 500, "price": p + 22},
            {"min_qty": 3000, "price": p + 8},
            {"min_qty": 10000, "price": p},
        ],
        sku_attributes={},
        delivery_region="Japan",
        lead_time_text="30-45 days",
        raw_response_id="raw_001",
        created_at=datetime.now(timezone.utc),
    )
    sample.usable_for_benchmark = True
    return sample


REQUIREMENT = {
    "id": "req-001",
    "product": "men's cotton shirt",
    "product_type": "men_cotton_shirt",
    "material": "100% cotton",
    "quantity": 10000,
    "unit": "piece",
    "process_tags": ["oem", "odm"],
    "target_market": "Japan",
    "source_platform": "mock_1688",
}

SUPPLIER_QUOTE_FOR_SERVICE = {
    "supplier_id": "sup_001",
    "unit_price": 38.5,
    "currency": "CNY",
    "unit": "piece",
    "moq": 10000,
}

SUPPLIER_QUOTE_FOR_CONTEXT = {
    "price": "38.5",
    "currency": "CNY",
    "unit": "piece",
    "moq": 10000,
}


@pytest.fixture
def samples():
    return [_make_shirt_sample(i) for i in range(1, 21)]


def test_context_bundle_builds_from_session_a_samples(samples):
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    context = retriever.build_context(
        requirement=REQUIREMENT,
        supplier_quote=SUPPLIER_QUOTE_FOR_CONTEXT,
        data_mode="mock",
    )
    assert len(context.evidence) == 20
    assert context.data_mode == "mock"
    assert context.supplier_quote is not None


def test_context_bundle_validates(samples):
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    context = retriever.build_context(
        requirement=REQUIREMENT,
        supplier_quote=SUPPLIER_QUOTE_FOR_CONTEXT,
        data_mode="mock",
    )
    validate_context_bundle(context)


def test_mock_qwen_produces_schema_locked_output(samples):
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    context = retriever.build_context(
        requirement=REQUIREMENT,
        supplier_quote=SUPPLIER_QUOTE_FOR_CONTEXT,
        data_mode="mock",
    )
    runtime = MockQwenRuntime()
    prompt = build_qwen_semantic_analysis_prompt(context)
    raw_output = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")

    validate_qwen_output(raw_output, context)
    analysis = QwenSemanticAnalysis(**raw_output)

    assert analysis.normalized_product_type == "men_cotton_shirt"
    assert analysis.normalized_material == "cotton"
    assert analysis.comparability_score == 0.85
    assert analysis.is_comparable is True


def test_qwen_evidence_ids_are_valid(samples):
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    context = retriever.build_context(
        requirement=REQUIREMENT,
        supplier_quote=SUPPLIER_QUOTE_FOR_CONTEXT,
        data_mode="mock",
    )
    runtime = MockQwenRuntime()
    prompt = build_qwen_semantic_analysis_prompt(context)
    raw_output = runtime.generate_json(prompt, schema_name="qwen_semantic_analysis")
    analysis = QwenSemanticAnalysis(**raw_output)

    valid_ids = context.evidence_ids()
    for eid in analysis.evidence_ids:
        assert eid in valid_ids, f"Evidence ID {eid!r} not in context bundle"


def test_session_b_benchmark_confidence_high(samples):
    service = GPMQuoteGuidanceService(llm_adapter=MockLLMAdapter())
    benchmark, guidance, _ = service.run(
        REQUIREMENT, samples, SUPPLIER_QUOTE_FOR_SERVICE
    )
    assert benchmark.comparable_sample_count >= 20
    assert benchmark.confidence_level == "high"


def test_session_b_supplier_quote_position(samples):
    service = GPMQuoteGuidanceService(llm_adapter=MockLLMAdapter())
    _, guidance, _ = service.run(
        REQUIREMENT, samples, SUPPLIER_QUOTE_FOR_SERVICE
    )
    assert guidance.supplier_quote_position == "within_high_range"


def test_session_b_recommendation_negotiate(samples):
    service = GPMQuoteGuidanceService(llm_adapter=MockLLMAdapter())
    _, guidance, _ = service.run(
        REQUIREMENT, samples, SUPPLIER_QUOTE_FOR_SERVICE
    )
    assert guidance.accept_recommendation == "negotiate"


def test_session_b_human_approval_required(samples):
    service = GPMQuoteGuidanceService(llm_adapter=MockLLMAdapter())
    _, guidance, _ = service.run(
        REQUIREMENT, samples, SUPPLIER_QUOTE_FOR_SERVICE
    )
    assert guidance.human_approval_required is True


def test_no_external_llm_import_in_context_package():
    import inspect
    import src.gpm.context as ctx_pkg
    source = ""
    import importlib
    for mod_name in [
        "src.gpm.context.evidence_reference",
        "src.gpm.context.gpm_context_bundle",
        "src.gpm.context.in_memory_context_retriever",
        "src.gpm.context.context_retriever",
    ]:
        mod = importlib.import_module(mod_name)
        try:
            source += inspect.getsource(mod)
        except OSError:
            pass
    for forbidden in ("openai", "anthropic", "dashscope", "google.generativeai", "deepseek"):
        assert forbidden not in source, f"Forbidden import {forbidden!r} found in context package"


def test_no_external_llm_import_in_qwen_package():
    import inspect
    import importlib
    source = ""
    for mod_name in [
        "src.gpm.qwen.mock_qwen_runtime",
        "src.gpm.qwen.qwen_runtime_config",
    ]:
        mod = importlib.import_module(mod_name)
        try:
            source += inspect.getsource(mod)
        except OSError:
            pass
    for forbidden in ("openai", "anthropic", "dashscope", "google.generativeai", "deepseek"):
        assert forbidden not in source, f"Forbidden import {forbidden!r} found in qwen package"
