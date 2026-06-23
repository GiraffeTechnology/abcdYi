"""Integration test: full Session A pipeline in mock mode.

PricingQuery -> Mock1688PricingAdapter -> validate_sample -> LocalJSONStore -> probe report
"""
from __future__ import annotations

import tempfile
from collections import Counter
from decimal import Decimal

from src.gpm.adapters.mock_1688_adapter import Mock1688PricingAdapter
from src.gpm.models.pricing_query import PricingQuery
from src.gpm.storage.local_json_store import LocalJSONStore


def test_mock_flow_end_to_end():
    query = PricingQuery(
        keyword="纯棉男士衬衫 OEM 定制",
        target_quantity=Decimal("10000"),
        target_unit="piece",
        max_samples=50,
        source_platform="1688",
    )

    adapter = Mock1688PricingAdapter()
    raw_response, samples = adapter.search_price_samples(query)

    with tempfile.TemporaryDirectory() as tmpdir:
        store = LocalJSONStore(base_dir=tmpdir)
        raw_id = store.save_raw_response(raw_response)
        sample_ids = store.save_price_samples(samples)
        loaded_samples = store.load_price_samples(sample_ids)

    valid_samples = [s for s in loaded_samples if s.usable_for_benchmark]
    invalid_samples = [s for s in loaded_samples if not s.usable_for_benchmark]

    reason_counts: Counter[str] = Counter()
    for s in invalid_samples:
        for r in s.invalid_reasons:
            reason_counts[r] += 1

    # Core acceptance criteria
    assert len(loaded_samples) >= 25, f"Expected >=25 samples, got {len(loaded_samples)}"
    assert len(valid_samples) >= 22, f"Expected >=22 valid, got {len(valid_samples)}"
    assert len(invalid_samples) >= 3, f"Expected >=3 invalid, got {len(invalid_samples)}"
    assert "missing_supplier_id" in reason_counts
    assert "missing_moq" in reason_counts
    assert "missing_observed_time" in reason_counts

    # All loaded samples must carry the persisted raw_response_id
    assert all(s.raw_response_id == raw_id for s in loaded_samples)

    # Valid samples must expose every Session B handoff field
    for s in valid_samples:
        assert s.id
        assert s.source_platform
        assert s.supplier_id
        assert s.captured_at or s.observed_at
        assert s.product_title
        assert s.price_min is not None or s.ladder_prices
        assert s.price_currency
        assert s.price_unit
        assert s.moq is not None
        assert s.raw_response_id
        assert s.usable_for_benchmark
