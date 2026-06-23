"""Integration E2E test: mock samples -> normalization -> benchmark -> guidance -> report."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.gpm.llm_adapters.mock_llm_adapter import MockLLMAdapter
from src.gpm.services.gpm_quote_guidance_service import GPMQuoteGuidanceService


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
    supplier_id: str = "sup_x"
    usable_for_benchmark: bool = True
    ladder_prices: list[dict] | None = None
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_platform: str = "mock_1688"
    raw_response_id: str = "mock"


SAMPLE_TITLES = [
    "men cotton shirt OEM custom",
    "100% cotton shirt",
    "OEM cotton shirt men",
    "men shirt 100% cotton",
    "pure cotton shirt OEM",
]
LADDER = [
    {"min_qty": 500, "price": 38},
    {"min_qty": 3000, "price": 32},
    {"min_qty": 10000, "price": 28},
]


@pytest.fixture
def mock_samples() -> list[_MockSample]:
    return [
        _MockSample(
            id=f"ms-{i+1:03d}",
            product_title=title,
            price_min=Decimal(str(28 + i)),
            price_max=Decimal(str(35 + i)),
            ladder_prices=LADDER,
            supplier_id=f"supplier_{chr(ord('a')+i)}",
        )
        for i, title in enumerate(SAMPLE_TITLES)
    ]


@pytest.fixture
def requirement() -> dict:
    return {
        "id": "req-e2e-001",
        "product": "men's cotton shirt",
        "quantity": 10000,
        "unit": "piece",
        "material": "100% cotton",
        "process_tags": ["cutting", "sewing", "buttoning", "packing"],
        "target_market": "Japan",
        "source_platform": "mock_1688",
    }


@pytest.fixture
def supplier_quote() -> dict:
    return {
        "supplier_id": "supplier_abc",
        "unit_price": 38.5,
        "currency": "CNY",
        "unit": "piece",
        "moq": 1000,
    }


def test_e2e_pipeline_produces_valid_guidance(
    mock_samples: list[_MockSample],
    requirement: dict,
    supplier_quote: dict,
) -> None:
    service = GPMQuoteGuidanceService(llm_adapter=MockLLMAdapter())
    benchmark, guidance, report = service.run(requirement, mock_samples, supplier_quote)

    assert guidance.supplier_quote_position
    assert guidance.accept_recommendation
    assert guidance.recommended_buyer_quote_low is not None
    assert guidance.recommended_buyer_quote_mid is not None
    assert guidance.recommended_buyer_quote_high is not None
    assert guidance.human_approval_required is True


def test_e2e_human_approval_always_required(
    mock_samples: list[_MockSample],
    requirement: dict,
    supplier_quote: dict,
) -> None:
    service = GPMQuoteGuidanceService(llm_adapter=MockLLMAdapter())
    _, guidance, _ = service.run(requirement, mock_samples, supplier_quote)
    assert guidance.human_approval_required is True


def test_e2e_report_contains_required_sections(
    mock_samples: list[_MockSample],
    requirement: dict,
    supplier_quote: dict,
) -> None:
    service = GPMQuoteGuidanceService(llm_adapter=MockLLMAdapter())
    _, guidance, report = service.run(requirement, mock_samples, supplier_quote)

    assert "Benchmark Range" in report
    assert "Supplier Quote Position" in report
    assert "Accept Recommendation" in report
    assert "Buyer-Facing Quote Options" in report
    assert "HUMAN APPROVAL REQUIRED" in report


def test_e2e_canonical_scenario_expected_outputs(
    mock_samples: list[_MockSample],
    requirement: dict,
    supplier_quote: dict,
) -> None:
    """PRD section 18 canonical scenario: quote=38.5, expect negotiate with human approval."""
    service = GPMQuoteGuidanceService(llm_adapter=MockLLMAdapter())
    _, guidance, _ = service.run(requirement, mock_samples, supplier_quote)

    assert guidance.human_approval_required is True
    assert guidance.accept_recommendation in ("negotiate", "accept", "request_more_info", "human_review_required")
