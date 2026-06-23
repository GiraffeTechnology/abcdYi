from __future__ import annotations

from decimal import Decimal

from src.gpm.adapters.mock_1688_adapter import Mock1688PricingAdapter
from src.gpm.models.pricing_query import PricingQuery


def _canonical_query() -> PricingQuery:
    return PricingQuery(
        keyword="纯棉男士衬衫 OEM 定制",
        target_quantity=Decimal("10000"),
        target_unit="piece",
        max_samples=50,
        source_platform="1688",
    )


def test_mock_adapter_returns_at_least_25_samples():
    adapter = Mock1688PricingAdapter()
    _, samples = adapter.search_price_samples(_canonical_query())
    assert len(samples) >= 25


def test_at_least_22_samples_are_valid():
    adapter = Mock1688PricingAdapter()
    _, samples = adapter.search_price_samples(_canonical_query())
    valid = [s for s in samples if s.usable_for_benchmark]
    assert len(valid) >= 22


def test_invalid_samples_are_preserved_but_excluded():
    adapter = Mock1688PricingAdapter()
    _, samples = adapter.search_price_samples(_canonical_query())
    invalid = [s for s in samples if not s.usable_for_benchmark]
    assert len(invalid) >= 3
    assert all(len(s.invalid_reasons) > 0 for s in invalid)


def test_raw_response_id_exists_for_all_samples():
    adapter = Mock1688PricingAdapter()
    raw_response, samples = adapter.search_price_samples(_canonical_query())
    assert all(s.raw_response_id == raw_response.id for s in samples)
