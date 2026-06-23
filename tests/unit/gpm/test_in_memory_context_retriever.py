"""Tests for InMemoryGPMContextRetriever."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.gpm.context.in_memory_context_retriever import InMemoryGPMContextRetriever


@dataclass
class _MockSample:
    id: str
    product_title: str
    price_min: Decimal = Decimal("30")
    price_max: Decimal = Decimal("38")
    price_currency: str = "CNY"
    price_unit: str = "piece"
    moq: Decimal = Decimal("1000")
    moq_unit: str = "piece"
    material: str = "cotton"
    source_platform: str = "mock_1688"
    usable_for_benchmark: bool = True
    invalid_reasons: list[str] = field(default_factory=list)
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


REQUIREMENT = {"id": "req-001", "product": "men's cotton shirt", "quantity": 10000}
SUPPLIER_QUOTE = {"supplier_id": "sup_a", "unit_price": 38.5, "currency": "CNY", "unit": "piece", "moq": 1000}


def _make_samples(n: int = 5) -> list[_MockSample]:
    return [
        _MockSample(id=f"ms-{i+1:03d}", product_title=f"cotton shirt men {i}")
        for i in range(n)
    ]


def test_samples_converted_to_evidence() -> None:
    retriever = InMemoryGPMContextRetriever(price_samples=_make_samples(3))
    bundle = retriever.build_context(REQUIREMENT, SUPPLIER_QUOTE)
    assert len(bundle.evidence) == 3


def test_evidence_ids_are_unique() -> None:
    samples = _make_samples(5)
    retriever = InMemoryGPMContextRetriever(price_samples=samples)
    bundle = retriever.build_context(REQUIREMENT, SUPPLIER_QUOTE)
    ids = [e.id for e in bundle.evidence]
    assert len(ids) == len(set(ids))


def test_invalid_sample_marked_unusable() -> None:
    bad = _MockSample(
        id="ms-bad",
        product_title="unrelated product",
        usable_for_benchmark=False,
        invalid_reasons=["wrong_category"],
    )
    retriever = InMemoryGPMContextRetriever(price_samples=[bad])
    bundle = retriever.build_context(REQUIREMENT, None)
    ev = bundle.evidence[0]
    assert not ev.usable_for_analysis
    assert "wrong_category" in ev.invalid_reasons


def test_valid_sample_passes_to_prompt_payload() -> None:
    retriever = InMemoryGPMContextRetriever(price_samples=_make_samples(3))
    bundle = retriever.build_context(REQUIREMENT, None)
    payload = bundle.to_prompt_payload()
    assert len(payload["evidence_ids"]) == 3


def test_limit_parameter_respected() -> None:
    retriever = InMemoryGPMContextRetriever(price_samples=_make_samples(20))
    bundle = retriever.build_context(REQUIREMENT, None, limit=5)
    assert len(bundle.evidence) == 5


def test_data_mode_passed_through() -> None:
    retriever = InMemoryGPMContextRetriever(price_samples=_make_samples(2))
    bundle = retriever.build_context(REQUIREMENT, None, data_mode="private")
    assert bundle.data_mode == "private"


def test_supplier_quote_stored_in_bundle() -> None:
    retriever = InMemoryGPMContextRetriever(price_samples=_make_samples(2))
    bundle = retriever.build_context(REQUIREMENT, SUPPLIER_QUOTE)
    assert bundle.supplier_quote == SUPPLIER_QUOTE


def test_dict_samples_also_work() -> None:
    dict_samples = [
        {"id": "d-001", "product_title": "cotton shirt", "price_min": "30", "usable_for_benchmark": True}
    ]
    retriever = InMemoryGPMContextRetriever(price_samples=dict_samples)
    bundle = retriever.build_context(REQUIREMENT, None)
    assert len(bundle.evidence) == 1
    assert bundle.evidence[0].id == "ev_d-001"
