"""Unit tests for QuoteGuidanceEngine."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from src.gpm.models.benchmark_snapshot import GPMBenchmarkSnapshot
from src.gpm.pricing.quote_guidance_engine import QuoteGuidanceEngine


def _bench(
    low: str = "25",
    median: str = "32",
    high: str = "38",
    confidence: str = "high",
    target_qty: str = "10000",
) -> GPMBenchmarkSnapshot:
    return GPMBenchmarkSnapshot(
        query_keyword="shirt",
        source_platform="mock",
        sample_count=20,
        comparable_sample_count=20,
        excluded_sample_count=0,
        confidence_level=confidence,
        confidence_reason="test",
        benchmark_low=Decimal(low),
        benchmark_median=Decimal(median),
        benchmark_high=Decimal(high),
        target_quantity=Decimal(target_qty),
        target_quantity_unit="piece",
    )


def _quote(price: str, moq: str | None = "1000") -> dict:
    q: dict = {"supplier_id": "sup_a", "unit_price": price, "currency": "CNY", "unit": "piece"}
    if moq is not None:
        q["moq"] = moq
    return q


def _req(qty: int = 10000) -> dict:
    return {"product": "shirt", "quantity": qty}


engine = QuoteGuidanceEngine()


def test_below_market_triggers_request_more_info() -> None:
    bench = _bench(low="25", median="32", high="38")
    guidance = engine.generate_guidance(_req(), _quote("10"), bench)
    assert guidance.accept_recommendation == "request_more_info"
    assert guidance.supplier_quote_position == "below_market"
    assert "possible_quality_or_scope_mismatch" in guidance.risk_flags


def test_within_low_range_triggers_accept() -> None:
    bench = _bench(low="25", median="32", high="38")
    guidance = engine.generate_guidance(_req(), _quote("28"), bench)
    assert guidance.accept_recommendation == "accept"
    assert guidance.supplier_quote_position == "within_low_range"


def test_within_high_range_triggers_negotiate() -> None:
    bench = _bench(low="25", median="32", high="38")
    guidance = engine.generate_guidance(_req(), _quote("36"), bench)
    assert guidance.accept_recommendation == "negotiate"
    assert "high_range" in guidance.supplier_quote_position or "mid_range" in guidance.supplier_quote_position


def test_above_market_triggers_negotiate() -> None:
    bench = _bench(low="25", median="32", high="38")
    guidance = engine.generate_guidance(_req(), _quote("42"), bench)
    assert guidance.accept_recommendation == "negotiate"
    assert guidance.supplier_quote_position == "above_market"


def test_far_above_market_triggers_reject() -> None:
    bench = _bench(low="25", median="32", high="38")
    guidance = engine.generate_guidance(_req(), _quote("60"), bench)
    assert guidance.accept_recommendation == "reject"
    assert guidance.supplier_quote_position == "above_market"


def test_missing_moq_triggers_human_review() -> None:
    bench = _bench()
    guidance = engine.generate_guidance(_req(), _quote("28", moq=None), bench)
    assert guidance.accept_recommendation == "human_review_required"
    assert "missing_supplier_moq" in guidance.risk_flags


def test_moq_above_target_quantity_triggers_negotiate() -> None:
    bench = _bench()
    guidance = engine.generate_guidance(_req(qty=10000), _quote("28", moq="20000"), bench)
    assert "moq_exceeds_target_quantity" in guidance.risk_flags
    assert guidance.accept_recommendation in ("negotiate", "human_review_required")


def test_human_approval_always_true() -> None:
    bench = _bench()
    for price in ("10", "28", "36", "60"):
        guidance = engine.generate_guidance(_req(), _quote(price), bench)
        assert guidance.human_approval_required is True


def test_buyer_quote_options_calculated_correctly() -> None:
    bench = _bench()
    policy = {"low_margin": Decimal("0.12"), "target_margin": Decimal("0.20"), "premium_margin": Decimal("0.32")}
    guidance = engine.generate_guidance(_req(), _quote("28"), bench, margin_policy=policy)
    assert guidance.recommended_buyer_quote_low == Decimal("28") * Decimal("1.12")
    assert guidance.recommended_buyer_quote_mid == Decimal("28") * Decimal("1.20")
    assert guidance.recommended_buyer_quote_high == Decimal("28") * Decimal("1.32")


def test_low_confidence_benchmark_returns_insufficient_data() -> None:
    bench = _bench(confidence="low")
    guidance = engine.generate_guidance(_req(), _quote("28"), bench)
    assert guidance.supplier_quote_position == "insufficient_data"
    assert guidance.accept_recommendation == "human_review_required"


# Regression: canonical 20-record seed distribution
# Prices: [round(3.20 + i * 0.042, 3) for i in range(20)] → P25=3.3995, P50=3.599, P75=3.7985
# seed_gpm_e2e_canonical_evidence.py must use supplier_quote=3.78 (not 4.20).
_CANONICAL_BENCH = _bench(low="3.3995", median="3.599", high="3.7985", confidence="high")


def test_canonical_seed_quote_within_high_range() -> None:
    # 3.78 sits between P50 (3.599) and P75 (3.7985) → within_high_range / negotiate
    guidance = engine.generate_guidance(
        _req(qty=10000),
        _quote("3.78", moq="1000"),
        _CANONICAL_BENCH,
    )
    assert guidance.supplier_quote_position == "within_high_range"
    assert guidance.accept_recommendation == "negotiate"
    assert guidance.human_approval_required is True


def test_canonical_seed_wrong_quote_above_market() -> None:
    # 4.20 exceeds P75 (3.7985) — former seed value was incorrect
    guidance = engine.generate_guidance(
        _req(qty=10000),
        _quote("4.20", moq="1000"),
        _CANONICAL_BENCH,
    )
    assert guidance.supplier_quote_position == "above_market"
