"""Integration tests: GPMSemanticQuoteService with GiraffeDBContextRetriever + mock HTTP transport."""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import httpx
import pytest

from src.gpm.clients.giraffe_db_client import GiraffeDBClient
from src.gpm.context.retrievers.giraffe_db_context_retriever import GiraffeDBContextRetriever
from src.gpm.llm_adapters.qwen_local_runtime import QwenLocalRuntime
from src.gpm.qwen.qwen_runtime_config import QwenRuntimeConfig
from src.gpm.services.gpm_semantic_quote_service import GPMSemanticQuoteService

_CANONICAL_PRICES = [round(24.0 + i * 1.16, 2) for i in range(20)]

_CANONICAL_GIRAFFE_DB_RESPONSE: dict[str, Any] = {
    "id": "ctx_canonical_001",
    "tenant_id": "tenant_001",
    "project_id": "project_001",
    "rfq_id": "rfq_001",
    "created_at": "2024-01-01T00:00:00+00:00",
    "pricing_context": {
        "rfq": {
            "id": "rfq_001",
            "product": "men's cotton shirt",
            "quantity": 10000,
            "unit": "piece",
            "material": "100% cotton",
            "process_tags": ["cutting", "sewing", "buttoning", "packing"],
            "target_market": "Japan",
            "source_platform": "mock_1688",
        },
        "pricing_evidence": [
            {
                "id": f"pe_{i+1:03d}",
                "source_type": "public_api",
                "source_id": f"pe_{i+1:03d}",
                "source_platform": "mock_1688",
                "raw_payload_hash": None,
                "created_at": "2024-01-01T00:00:00+00:00",
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
    """In-process HTTP transport for test isolation — no live giraffe-db required."""

    def __init__(self, route_responses: dict[str, Any]) -> None:
        self._route_responses = route_responses

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        for pattern, response_data in self._route_responses.items():
            if pattern in path:
                return httpx.Response(
                    200,
                    content=json.dumps(response_data).encode(),
                    headers={"content-type": "application/json"},
                )
        return httpx.Response(
            404,
            content=json.dumps({"detail": "not found"}).encode(),
            headers={"content-type": "application/json"},
        )


@pytest.fixture
def service() -> GPMSemanticQuoteService:
    transport = _MockTransport({"/gpm/context": _CANONICAL_GIRAFFE_DB_RESPONSE})
    client = GiraffeDBClient(
        base_url="http://giraffe-db-test",
        tenant_id="tenant_001",
        transport=transport,
    )
    retriever = GiraffeDBContextRetriever(client=client, default_tenant_id="tenant_001")
    runtime = QwenLocalRuntime(config=QwenRuntimeConfig(runtime_mode="mock"))
    return GPMSemanticQuoteService(context_retriever=retriever, qwen_runtime=runtime)


def test_service_with_giraffe_db_retriever_runs(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    assert isinstance(output, dict)
    assert output["human_approval_required"] is True


def test_service_with_giraffe_db_retriever_canonical_quote_position(service: GPMSemanticQuoteService) -> None:
    """Canonical 20 samples + 38.5 supplier quote must yield within_high_range → negotiate."""
    output = service.run()
    assert output["supplier_quote_position"] == "within_high_range"
    assert output["accept_recommendation"] == "negotiate"


def test_service_with_giraffe_db_retriever_runtime_mode(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    assert output["runtime_mode"] == "mock"


def test_service_with_giraffe_db_retriever_has_context_bundle_id(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    assert output["context_bundle_id"] == "ctx_canonical_001"


def test_service_with_giraffe_db_retriever_has_benchmark_snapshot(service: GPMSemanticQuoteService) -> None:
    output = service.run()
    snapshot = output["benchmark_snapshot"]
    assert snapshot["comparable_sample_count"] == 20
    assert snapshot["confidence"] == "high"


def test_service_with_giraffe_db_retriever_old_kwarg_names_still_work() -> None:
    """Backward-compat: GPMSemanticQuoteService(retriever=..., runtime=...) must still work."""
    transport = _MockTransport({"/gpm/context": _CANONICAL_GIRAFFE_DB_RESPONSE})
    client = GiraffeDBClient(
        base_url="http://giraffe-db-test",
        transport=transport,
    )
    retriever = GiraffeDBContextRetriever(client=client)
    runtime = QwenLocalRuntime(config=QwenRuntimeConfig(runtime_mode="mock"))
    # Old keyword argument names
    service = GPMSemanticQuoteService(retriever=retriever, runtime=runtime)
    output = service.run()
    assert output["human_approval_required"] is True
