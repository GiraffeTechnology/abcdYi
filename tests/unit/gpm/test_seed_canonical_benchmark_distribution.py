"""Regression test: canonical 20-record seed produces correct benchmark distribution.

Validates that the price series used in scripts/seed_gpm_e2e_canonical_evidence.py
(3.200–3.998 USD, step 0.042, 20 samples) produces benchmark values that make
supplier_quote=3.76 USD land in within_high_range / negotiate — the expected
E2E result documented in GPM_A_F_UNIFIED_DB_LLM_E2E_TEST_REPORT.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.gpm.models.semantic_normalization import GPMSemanticNormalization
from src.gpm.pricing.benchmark_engine import BenchmarkEngine
from src.gpm.pricing.quote_guidance_engine import QuoteGuidanceEngine

_SEED_PRICES_USD = [round(3.20 + i * 0.042, 3) for i in range(20)]
_SUPPLIER_QUOTE_USD = 3.76


@dataclass
class _SeedSample:
    id: str
    product_title: str
    price_min: Decimal
    price_max: Decimal | None = None
    price_unit: str = "piece"
    usable_for_benchmark: bool = True
    ladder_prices: list[dict] = field(default_factory=list)
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_platform: str = "mock_1688"


def _make_seed_samples() -> tuple[list[_SeedSample], list[GPMSemanticNormalization]]:
    samples = []
    norms = []
    for i, price in enumerate(_SEED_PRICES_USD):
        sid = f"ev-e2e-canonical-{i+1:03d}"
        samples.append(_SeedSample(
            id=sid,
            product_title=f"men cotton shirt OEM canonical {i+1}",
            price_min=Decimal(str(price)),
        ))
        norms.append(GPMSemanticNormalization(
            sample_id=sid,
            is_comparable=True,
            comparability_score=Decimal("0.90"),
            reason="canonical seed",
            normalized_product_type="men_cotton_shirt",
            normalized_material="cotton",
            normalized_process_tags=["cutting", "sewing", "buttoning", "packing"],
        ))
    return samples, norms


_SEED_REQUIREMENT = {
    "product": "men cotton shirt",
    "quantity": 10000,
    "unit": "piece",
    "material": "100% cotton",
    "source_platform": "mock_1688",
}

_SEED_SUPPLIER_QUOTE = {
    "unit_price": _SUPPLIER_QUOTE_USD,
    "currency": "USD",
    "moq": 1000,
}


@pytest.fixture(scope="module")
def seed_benchmark():
    samples, norms = _make_seed_samples()
    engine = BenchmarkEngine()
    return engine.build_benchmark(_SEED_REQUIREMENT, samples, norms)


def test_seed_price_range_is_correct():
    assert _SEED_PRICES_USD[0] == pytest.approx(3.200)
    assert _SEED_PRICES_USD[-1] == pytest.approx(3.998)
    assert len(_SEED_PRICES_USD) == 20


def test_seed_confidence_is_high(seed_benchmark):
    assert seed_benchmark.confidence_level == "high"
    assert seed_benchmark.comparable_sample_count == 20


def test_seed_benchmark_low_p25(seed_benchmark):
    # P25 of [3.200 … 3.998] step 0.042: idx=4.75 → 3.368 + 0.75*0.042 ≈ 3.3995
    assert seed_benchmark.benchmark_low is not None
    assert float(seed_benchmark.benchmark_low) == pytest.approx(3.3995, abs=1e-4)


def test_seed_benchmark_median_p50(seed_benchmark):
    # P50: idx=9.5 → 3.578 + 0.5*0.042 ≈ 3.5990
    assert seed_benchmark.benchmark_median is not None
    assert float(seed_benchmark.benchmark_median) == pytest.approx(3.5990, abs=1e-4)


def test_seed_benchmark_high_p75(seed_benchmark):
    # P75: idx=14.25 → 3.788 + 0.25*0.042 ≈ 3.7985
    assert seed_benchmark.benchmark_high is not None
    assert float(seed_benchmark.benchmark_high) == pytest.approx(3.7985, abs=1e-4)


def test_supplier_quote_3_76_is_above_within_high_range_lower_bound(seed_benchmark):
    # Lower bound of within_high_range: (P50 + P75) / 2 ≈ 3.6987
    med = float(seed_benchmark.benchmark_median)
    high = float(seed_benchmark.benchmark_high)
    lower_bound = (med + high) / 2
    assert lower_bound == pytest.approx(3.6987, abs=1e-3)
    assert _SUPPLIER_QUOTE_USD > lower_bound


def test_supplier_quote_3_76_is_below_or_equal_benchmark_high(seed_benchmark):
    # 3.76 must be ≤ P75 ≈ 3.7985 to land in within_high_range (not above_market)
    high = float(seed_benchmark.benchmark_high)
    assert _SUPPLIER_QUOTE_USD <= high


def test_seed_quote_position_is_within_high_range(seed_benchmark):
    guidance = QuoteGuidanceEngine().generate_guidance(
        _SEED_REQUIREMENT,
        _SEED_SUPPLIER_QUOTE,
        seed_benchmark,
    )
    assert guidance.supplier_quote_position == "within_high_range", (
        f"Expected within_high_range but got {guidance.supplier_quote_position}. "
        f"benchmark: low={seed_benchmark.benchmark_low}, "
        f"median={seed_benchmark.benchmark_median}, "
        f"high={seed_benchmark.benchmark_high}, "
        f"quote={_SUPPLIER_QUOTE_USD}"
    )


def test_seed_recommendation_is_negotiate(seed_benchmark):
    guidance = QuoteGuidanceEngine().generate_guidance(
        _SEED_REQUIREMENT,
        _SEED_SUPPLIER_QUOTE,
        seed_benchmark,
    )
    assert guidance.accept_recommendation == "negotiate"


def test_seed_human_approval_required(seed_benchmark):
    guidance = QuoteGuidanceEngine().generate_guidance(
        _SEED_REQUIREMENT,
        _SEED_SUPPLIER_QUOTE,
        seed_benchmark,
    )
    assert guidance.human_approval_required is True
