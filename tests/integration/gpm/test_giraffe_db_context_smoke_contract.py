"""Smoke-contract tests: GiraffeDBContextRetriever + mapper end-to-end with mock HTTP transport."""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import httpx
import pytest

from src.gpm.clients.giraffe_db_client import GiraffeDBClient, GiraffeDBClientError
from src.gpm.context.retrievers.giraffe_db_context_retriever import GiraffeDBContextRetriever
from src.gpm.context.gpm_context_bundle import GPMContextBundle

_CANONICAL_PRICES = [round(24.0 + i * 1.16, 2) for i in range(20)]

_CANONICAL_RESPONSE: dict[str, Any] = {
    "id": "ctx_smoke_001",
    "tenant_id": "tenant_smoke",
    "project_id": "project_smoke",
    "rfq_id": "rfq_smoke",
    "created_at": "2025-01-15T08:30:00+00:00",
    "pricing_context": {
        "rfq": {
            "id": "rfq_smoke",
            "product": "men's cotton shirt",
            "quantity": 10000,
            "unit": "piece",
            "material": "100% cotton",
            "source_platform": "mock_1688",
        },
        "pricing_evidence": [
            {
                "id": f"pe_{i+1:03d}",
                "source_type": "public_api",
                "source_id": f"pe_{i+1:03d}",
                "source_platform": "mock_1688",
                "raw_payload_hash": f"hash_{i+1:03d}",
                "created_at": "2025-01-15T08:30:00+00:00",
                "payload": {
                    "product_title": f"men cotton shirt OEM {i+1}",
                    "price_min": str(_CANONICAL_PRICES[i]),
                    "price_currency": "CNY",
                    "price_unit": "piece",
                    "moq": "1000",
                    "material": "100% cotton",
                    "source_platform": "mock_1688",
                },
                "usable_for_benchmark": True,
                "invalid_reasons": [],
            }
            for i in range(20)
        ],
        "imported_api_records": [],
        "public_benchmark_sample": [],
        "supplier_response_packets": [],
        "private_data_records": [],
        "private_customer_quote_history": [],
        "system_generated_records": [],
        "supplier_quote": {"unit_price": "38.5", "currency": "CNY", "moq": "1000"},
        "evidence_ids": [f"pe_{i+1:03d}" for i in range(20)],
        "source_confidence": "persisted",
    },
    "evidence_ids": [f"pe_{i+1:03d}" for i in range(20)],
    "mock_mode": False,
}


class _MockTransport(httpx.BaseTransport):
    def __init__(self, response_data: dict) -> None:
        self._response_data = response_data
        self.last_request: httpx.Request | None = None
        self.last_request_body: dict | None = None

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.last_request = request
        try:
            self.last_request_body = json.loads(request.content)
        except Exception:
            self.last_request_body = None
        return httpx.Response(
            200,
            content=json.dumps(self._response_data).encode(),
            headers={"content-type": "application/json"},
        )


@pytest.fixture
def transport_and_retriever() -> tuple[_MockTransport, GiraffeDBContextRetriever]:
    transport = _MockTransport(_CANONICAL_RESPONSE)
    client = GiraffeDBClient(
        base_url="http://giraffe-db-smoke",
        tenant_id="tenant_smoke",
        transport=transport,
    )
    retriever = GiraffeDBContextRetriever(client=client, default_tenant_id="tenant_smoke")
    return transport, retriever


def test_smoke_retrieve_returns_bundle(
    transport_and_retriever: tuple[_MockTransport, GiraffeDBContextRetriever],
) -> None:
    _, retriever = transport_and_retriever
    bundle = retriever.retrieve()
    assert isinstance(bundle, GPMContextBundle)


def test_smoke_request_payload_has_include_private_data(
    transport_and_retriever: tuple[_MockTransport, GiraffeDBContextRetriever],
) -> None:
    transport, retriever = transport_and_retriever
    retriever.retrieve(include_private_data=False)
    assert transport.last_request_body is not None
    assert transport.last_request_body["include_private_data"] is False


def test_smoke_bundle_has_20_price_samples(
    transport_and_retriever: tuple[_MockTransport, GiraffeDBContextRetriever],
) -> None:
    _, retriever = transport_and_retriever
    bundle = retriever.retrieve()
    assert len(bundle.price_samples) == 20


def test_smoke_bundle_evidence_ids_match(
    transport_and_retriever: tuple[_MockTransport, GiraffeDBContextRetriever],
) -> None:
    _, retriever = transport_and_retriever
    bundle = retriever.retrieve()
    evidence_ids = {e.id for e in bundle.evidence}
    expected_ids = {f"pe_{i+1:03d}" for i in range(20)}
    assert evidence_ids == expected_ids


def test_smoke_data_mode_is_public(
    transport_and_retriever: tuple[_MockTransport, GiraffeDBContextRetriever],
) -> None:
    _, retriever = transport_and_retriever
    bundle = retriever.retrieve(include_private_data=False)
    assert bundle.data_mode == "public"


def test_smoke_supplier_quote_mapped(
    transport_and_retriever: tuple[_MockTransport, GiraffeDBContextRetriever],
) -> None:
    _, retriever = transport_and_retriever
    bundle = retriever.retrieve()
    assert bundle.supplier_quote is not None
    assert bundle.supplier_quote["unit_price"] == Decimal("38.5")
    assert bundle.supplier_quote["currency"] == "CNY"
