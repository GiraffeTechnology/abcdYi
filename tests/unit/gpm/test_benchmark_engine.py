"""Unit tests for BenchmarkEngine."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List

import pytest

from src.gpm.models.semantic_normalization import GPMSemanticNormalization
from src.gpm.pricing.benchmark_engine import BenchmarkEngine


@dataclass
class _Sample:
    id: str
    product_title: str
    price_min: Decimal
    price_max: Decimal
    usable_for_benchmark: bool = True
    ladder_prices: Optional[List[dict]] = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_platform: str = "mock"


def _norm(sid: str, score: float) -> GPMSemanticNormalization:
    return GPMSemanticNormalization(
        sample_id=sid,
        is_comparable=score >= 0.60,
        comparability_score=Decimal(str(score)),
        reason="test",
        normalized_product_type="men_cotton_shirt",
        normalized_material="cotton",
        normalized_process_tags=["sewing"],
    )


def _make_samples(n: int, price_start: int = 20) -> tuple[list[_Sample], list[GPMSemanticNormalization]]:
    samples = []
    norms = []
    for i in range(n):
        sid = f"s{i+1}"
        price = Decimal(str(price_start + i))
        samples.append(_Sample(id=sid, product_title="cotton shirt", price_min=price, price_max=price))
        norms.append(_norm(sid, 0.85))
    return samples, norms


def _req(qty: int = 10000) -> dict:
    return {"product": "shirt", "quantity": qty, "unit": "piece", "source_platform": "mock"}


def test_benchmark_uses_only_valid_comparable_samples() -> None:
    samples, norms = _make_samples(5)
    bad_sample = _Sample(id="bad", product_title="bucket", price_min=Decimal("1"), price_max=Decimal("1"))
    bad_norm = _norm("bad", 0.10)
    engine = BenchmarkEngine()
    snap = engine.build_benchmark(_req(), samples + [bad_sample], norms + [bad_norm])
    assert snap.comparable_sample_count == 5
    assert snap.excluded_sample_count == 1


def test_percentile_p25_p50_p75_correct() -> None:
    samples, norms = _make_samples(4, price_start=10)
    engine = BenchmarkEngine()
    snap = engine.build_benchmark(_req(), samples, norms)
    assert snap.benchmark_low is not None
    assert snap.benchmark_median is not None
    assert snap.benchmark_high is not None
    assert snap.benchmark_low <= snap.benchmark_median <= snap.benchmark_high


def test_ladder_price_matching_target_quantity() -> None:
    ladder = [{"min_qty": 500, "price": 45}, {"min_qty": 3000, "price": 36}, {"min_qty": 10000, "price": 31}]
    sample = _Sample(
        id="s1", product_title="cotton shirt",
        price_min=Decimal("45"), price_max=Decimal("45"),
        ladder_prices=ladder,
    )
    norm = _norm("s1", 0.85)
    engine = BenchmarkEngine()
    snap = engine.build_benchmark({"product": "shirt", "quantity": 10000, "unit": "piece", "source_platform": "mock"}, [sample], [norm])
    assert snap.benchmark_median == Decimal("31")


def test_ladder_price_mid_tier() -> None:
    ladder = [{"min_qty": 500, "price": 45}, {"min_qty": 3000, "price": 36}, {"min_qty": 10000, "price": 31}]
    sample = _Sample(id="s1", product_title="cotton shirt", price_min=Decimal("45"), price_max=Decimal("45"), ladder_prices=ladder)
    norm = _norm("s1", 0.85)
    engine = BenchmarkEngine()
    snap = engine.build_benchmark({"product": "shirt", "quantity": 5000, "unit": "piece", "source_platform": "mock"}, [sample], [norm])
    assert snap.benchmark_median == Decimal("36")


def test_confidence_high_when_ge_20_samples() -> None:
    samples, norms = _make_samples(20)
    snap = BenchmarkEngine().build_benchmark(_req(), samples, norms)
    assert snap.confidence_level == "high"


def test_confidence_medium_when_between_10_and_19() -> None:
    samples, norms = _make_samples(15)
    snap = BenchmarkEngine().build_benchmark(_req(), samples, norms)
    assert snap.confidence_level == "medium"


def test_confidence_low_when_lt_10() -> None:
    samples, norms = _make_samples(5)
    snap = BenchmarkEngine().build_benchmark(_req(), samples, norms)
    assert snap.confidence_level == "low"
