from __future__ import annotations

from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.prompts.qwen_semantic_analysis_prompt import build_qwen_semantic_analysis_prompt
from src.gpm.prompts.qwen_quote_reasoning_prompt import build_qwen_quote_reasoning_prompt
from src.gpm.models.benchmark_snapshot import GPMBenchmarkSnapshot
from decimal import Decimal


def _make_context():
    return GPMContextBundle(
        bundle_id="b001",
        data_mode="mock",
        requirement={"product_type": "men_cotton_shirt", "quantity": 10000},
        evidence=[
            GPMEvidenceReference(id="ev_001", source_type="api_sample", source_id="s1"),
        ],
    )


def _make_benchmark():
    return GPMBenchmarkSnapshot(
        query_keyword="men cotton shirt",
        source_platform="mock",
        sample_count=20,
        comparable_sample_count=20,
        excluded_sample_count=0,
        confidence_level="high",
        confidence_reason="20 comparable samples",
        benchmark_low=Decimal("30.0"),
        benchmark_median=Decimal("35.5"),
        benchmark_high=Decimal("40.25"),
    )


def test_semantic_analysis_prompt_json_only():
    prompt = build_qwen_semantic_analysis_prompt(_make_context())
    assert "JSON only" in prompt


def test_semantic_analysis_prompt_no_invent_prices():
    prompt = build_qwen_semantic_analysis_prompt(_make_context())
    assert "Do not invent prices" in prompt


def test_semantic_analysis_prompt_no_invent_moq():
    prompt = build_qwen_semantic_analysis_prompt(_make_context())
    assert "Do not invent MOQ" in prompt


def test_semantic_analysis_prompt_cite_evidence_ids():
    prompt = build_qwen_semantic_analysis_prompt(_make_context())
    assert "evidence_ids" in prompt
    assert "cite" in prompt.lower()


def test_semantic_analysis_prompt_no_orders():
    prompt = build_qwen_semantic_analysis_prompt(_make_context())
    assert "Do not place orders" in prompt


def test_semantic_analysis_prompt_no_payment():
    prompt = build_qwen_semantic_analysis_prompt(_make_context())
    assert "payment" in prompt.lower()


def test_semantic_analysis_prompt_human_approval():
    prompt = build_qwen_semantic_analysis_prompt(_make_context())
    assert "Human approval" in prompt or "human approval" in prompt.lower()


def test_semantic_analysis_prompt_no_final_buyer_quote():
    prompt = build_qwen_semantic_analysis_prompt(_make_context())
    assert "Do not make final buyer quote decisions" in prompt


def test_quote_reasoning_prompt_json_only():
    ctx = _make_context()
    benchmark = _make_benchmark()
    prompt = build_qwen_quote_reasoning_prompt(
        ctx, benchmark, {"unit_price": 38.5, "currency": "CNY"}
    )
    assert "Return JSON only" in prompt


def test_quote_reasoning_prompt_no_margin_policy():
    ctx = _make_context()
    benchmark = _make_benchmark()
    prompt = build_qwen_quote_reasoning_prompt(
        ctx, benchmark, {"unit_price": 38.5, "currency": "CNY"}
    )
    assert "Do not set final margin policy" in prompt


def test_quote_reasoning_prompt_no_order_dispatch():
    ctx = _make_context()
    benchmark = _make_benchmark()
    prompt = build_qwen_quote_reasoning_prompt(
        ctx, benchmark, {"unit_price": 38.5, "currency": "CNY"}
    )
    assert "Human approval is required" in prompt
