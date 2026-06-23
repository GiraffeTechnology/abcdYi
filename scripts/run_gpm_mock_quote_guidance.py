#!/usr/bin/env python
"""Mock E2E script for GPM Session B quote guidance pipeline.

Runs without Session A API credentials or any live external calls.
Usage: uv run python scripts/run_gpm_mock_quote_guidance.py
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.gpm.llm_adapters.mock_llm_adapter import MockLLMAdapter
from src.gpm.services.gpm_quote_guidance_service import GPMQuoteGuidanceService


@dataclass
class MockSample:
    id: str
    product_title: str
    price_min: Decimal
    price_max: Decimal
    price_currency: str
    price_unit: str
    moq: Decimal
    moq_unit: str
    supplier_id: str
    usable_for_benchmark: bool = True
    ladder_prices: list[dict] | None = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    observed_at: datetime | None = None
    source_platform: str = "mock_1688"
    raw_response_id: str = "mock"


def load_or_generate_samples() -> list[MockSample]:
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "gpm" / "mock_1688_price_samples.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            raw = json.load(f)
        samples = []
        for item in raw:
            ladder = item.get("ladder_prices")
            samples.append(MockSample(
                id=item["id"],
                product_title=item["product_title"],
                price_min=Decimal(str(item.get("price_min", item.get("price_max", 0)))),
                price_max=Decimal(str(item.get("price_max", item.get("price_min", 0)))),
                price_currency=item.get("price_currency", "CNY"),
                price_unit=item.get("price_unit", "piece"),
                moq=Decimal(str(item.get("moq", 1000))),
                moq_unit=item.get("moq_unit", "piece"),
                supplier_id=item.get("supplier_id", "unknown"),
                usable_for_benchmark=item.get("usable_for_benchmark", True),
                ladder_prices=ladder,
                source_platform=item.get("source_platform", "mock_1688"),
            ))
        return samples

    titles = [
        "men cotton shirt OEM custom 定制纯棉衬衫",
        "100% cotton men shirt 纯棉男壱",
        "OEM cotton shirt 定制衬衫",
        "men shirt cotton 男壱纯棉",
        "pure cotton shirt OEM",
    ]
    prices = [
        (28, 32, [{"min_qty": 500, "price": 32}, {"min_qty": 3000, "price": 28}, {"min_qty": 10000, "price": 25}]),
        (30, 35, [{"min_qty": 500, "price": 35}, {"min_qty": 3000, "price": 30}, {"min_qty": 10000, "price": 27}]),
        (33, 38, [{"min_qty": 500, "price": 38}, {"min_qty": 3000, "price": 33}, {"min_qty": 10000, "price": 29}]),
        (35, 40, [{"min_qty": 500, "price": 40}, {"min_qty": 3000, "price": 35}, {"min_qty": 10000, "price": 31}]),
        (36, 42, [{"min_qty": 500, "price": 42}, {"min_qty": 3000, "price": 36}, {"min_qty": 10000, "price": 32}]),
    ]
    samples = []
    for i, (title, (pmin, pmax, ladder)) in enumerate(zip(titles, prices)):
        samples.append(MockSample(
            id=f"mock-sample-{i+1:03d}",
            product_title=title,
            price_min=Decimal(str(pmin)),
            price_max=Decimal(str(pmax)),
            price_currency="CNY",
            price_unit="piece",
            moq=Decimal("1000"),
            moq_unit="piece",
            supplier_id=f"supplier_{chr(ord('a') + i)}",
            usable_for_benchmark=True,
            ladder_prices=ladder,
        ))
    return samples


def main() -> int:
    requirement = {
        "id": "req-001",
        "product": "men's cotton shirt",
        "quantity": 10000,
        "unit": "piece",
        "material": "100% cotton",
        "process_tags": ["cutting", "sewing", "buttoning", "packing"],
        "target_market": "Japan",
        "source_platform": "mock_1688",
    }
    supplier_quote = {
        "supplier_id": "supplier_abc",
        "unit_price": 38.5,
        "currency": "CNY",
        "unit": "piece",
        "moq": 1000,
    }

    samples = load_or_generate_samples()
    service = GPMQuoteGuidanceService(llm_adapter=MockLLMAdapter())
    benchmark, guidance, report = service.run(requirement, samples, supplier_quote)

    print(report)
    print()

    expected_position = guidance.supplier_quote_position
    expected_rec = guidance.accept_recommendation
    assert guidance.human_approval_required is True, "human_approval_required must be True"

    print("GPM LIGHTWEIGHT MOCK QUOTE GUIDANCE: PASS")
    print(f"supplier_quote_position: {expected_position}")
    print(f"accept_recommendation: {expected_rec}")
    print(f"human_approval_required: {guidance.human_approval_required}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
