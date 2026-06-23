#!/usr/bin/env python3
"""GPM 1688 API probe — validates mock or live data ingestion pipeline.

Usage:
  uv run python scripts/gpm_1688_api_probe.py --mode mock
  GPM_ENABLE_LIVE_1688_TESTS=true uv run python scripts/gpm_1688_api_probe.py --mode live
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from decimal import Decimal

sys.path.insert(0, ".")

from src.gpm.adapters.mock_1688_adapter import Mock1688PricingAdapter
from src.gpm.models.pricing_query import PricingQuery
from src.gpm.storage.local_json_store import LocalJSONStore


def run_mock() -> int:
    query = PricingQuery(
        keyword="纯棉男士衬衫 OEM 定制",
        target_quantity=Decimal("10000"),
        target_unit="piece",
        max_samples=50,
        source_platform="1688",
    )

    adapter = Mock1688PricingAdapter()
    raw_response, samples = adapter.search_price_samples(query)

    store = LocalJSONStore()
    raw_id = store.save_raw_response(raw_response)
    store.save_price_samples(samples)

    valid = [s for s in samples if s.usable_for_benchmark]
    invalid = [s for s in samples if not s.usable_for_benchmark]

    reason_counts: Counter[str] = Counter()
    for s in invalid:
        for r in s.invalid_reasons:
            reason_counts[r] += 1

    print("GPM 1688 API PROBE: PASS")
    print(f"raw_response_id: {raw_id}")
    print(f"sample_count: {len(samples)}")
    print(f"valid_sample_count: {len(valid)}")
    print(f"invalid_sample_count: {len(invalid)}")
    if reason_counts:
        print("invalid_reasons:")
        for reason, count in sorted(reason_counts.items()):
            print(f"  {reason}: {count}")

    assert len(samples) >= 25, f"Expected >=25 samples, got {len(samples)}"
    assert len(valid) >= 22, f"Expected >=22 valid samples, got {len(valid)}"
    assert len(invalid) >= 3, f"Expected >=3 invalid samples, got {len(invalid)}"

    return 0


def run_live() -> int:
    if os.environ.get("GPM_ENABLE_LIVE_1688_TESTS", "").lower() != "true":
        print("ERROR: GPM_ENABLE_LIVE_1688_TESTS must be set to 'true' for live mode.")
        return 1

    from src.gpm.adapters.real_1688_adapter import Real1688PricingAdapter

    adapter = Real1688PricingAdapter()
    query = PricingQuery(
        keyword="纯棉男士衬衫 OEM 定制",
        target_quantity=Decimal("10000"),
        target_unit="piece",
        max_samples=50,
        source_platform="1688",
    )
    try:
        raw_response, samples = adapter.search_price_samples(query)
        print("GPM 1688 API PROBE (LIVE): called search_price_samples")
        print(f"raw_response_id: {raw_response.id}")
        print(f"sample_count: {len(samples)}")
    except NotImplementedError as exc:
        print(f"Live adapter not yet implemented: {exc}")
        return 1

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="GPM 1688 API probe")
    parser.add_argument("--mode", choices=["mock", "live"], default="mock")
    args = parser.parse_args()

    if args.mode == "mock":
        return run_mock()
    return run_live()


if __name__ == "__main__":
    sys.exit(main())
