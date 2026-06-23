"""Tests for MockContextRetriever canonical cotton shirt scenario."""
from __future__ import annotations

import pytest

from src.gpm.context.mock_context_retriever import (
    MockContextRetriever,
    CANONICAL_REQUIREMENT,
    CANONICAL_SUPPLIER_QUOTE,
)


@pytest.fixture
def retriever() -> MockContextRetriever:
    return MockContextRetriever()


def test_build_gpm_context_returns_bundle(retriever: MockContextRetriever) -> None:
    bundle = retriever.build_gpm_context(
        tenant_id=None, project_id=None, rfq_id=None, supplier_response_id=None
    )
    assert bundle is not None
    assert bundle.bundle_id


def test_canonical_requirement_present(retriever: MockContextRetriever) -> None:
    bundle = retriever.build_gpm_context(
        tenant_id=None, project_id=None, rfq_id=None, supplier_response_id=None
    )
    assert bundle.requirement["product"] == "men's cotton shirt"
    assert bundle.requirement["quantity"] == 10000


def test_canonical_supplier_quote_present(retriever: MockContextRetriever) -> None:
    bundle = retriever.build_gpm_context(
        tenant_id=None, project_id=None, rfq_id=None, supplier_response_id=None
    )
    assert bundle.supplier_quote is not None
    assert float(bundle.supplier_quote["unit_price"]) == 38.5


def test_bundle_has_20_evidence_items(retriever: MockContextRetriever) -> None:
    bundle = retriever.build_gpm_context(
        tenant_id=None, project_id=None, rfq_id=None, supplier_response_id=None
    )
    assert len(bundle.evidence) == 20


def test_evidence_ids_are_unique(retriever: MockContextRetriever) -> None:
    bundle = retriever.build_gpm_context(
        tenant_id=None, project_id=None, rfq_id=None, supplier_response_id=None
    )
    ids = [e.id for e in bundle.evidence]
    assert len(ids) == len(set(ids))


def test_price_samples_include_prices(retriever: MockContextRetriever) -> None:
    bundle = retriever.build_gpm_context(
        tenant_id=None, project_id=None, rfq_id=None, supplier_response_id=None
    )
    # Price samples must have price_min for benchmark engine
    for s in bundle.price_samples:
        assert "price_min" in s, f"Sample missing price_min: {s}"


def test_data_mode_is_mock(retriever: MockContextRetriever) -> None:
    bundle = retriever.build_gpm_context(
        tenant_id=None, project_id=None, rfq_id=None, supplier_response_id=None
    )
    assert bundle.data_mode == "mock"


def test_tenant_id_passed_through(retriever: MockContextRetriever) -> None:
    bundle = retriever.build_gpm_context(
        tenant_id="tenant_abc", project_id=None, rfq_id=None, supplier_response_id=None
    )
    assert bundle.tenant_id == "tenant_abc"


def test_public_and_private_evidence_separation(retriever: MockContextRetriever) -> None:
    bundle = retriever.build_gpm_context(
        tenant_id=None, project_id=None, rfq_id=None,
        supplier_response_id=None, include_private_data=False,
    )
    # In mock mode all samples are public; no private evidence required
    assert bundle.private_order_history == []


def test_canonical_scenario_produces_cotton_shirt_titles(retriever: MockContextRetriever) -> None:
    bundle = retriever.build_gpm_context(
        tenant_id=None, project_id=None, rfq_id=None, supplier_response_id=None
    )
    for s in bundle.price_samples:
        title = s.get("product_title", "").lower()
        assert "shirt" in title or "cotton" in title
