"""Unit tests for GiraffeDBContextRetriever."""
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from src.gpm.clients.giraffe_db_client import GiraffeDBClientError
from src.gpm.context.retrievers.giraffe_db_context_retriever import GiraffeDBContextRetriever
from src.gpm.context.gpm_context_bundle import GPMContextBundle


def _minimal_api_response(
    ctx_id: str = "ctx_001",
    pricing_evidence: list | None = None,
) -> dict:
    return {
        "id": ctx_id,
        "tenant_id": "tenant_001",
        "project_id": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "pricing_context": {
            "rfq": {"product": "test product", "quantity": 100, "unit": "piece"},
            "pricing_evidence": pricing_evidence or [
                {
                    "id": "pe_001",
                    "source_type": "public_api",
                    "source_id": "pe_001",
                    "source_platform": "mock_1688",
                    "raw_payload_hash": None,
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "payload": {
                        "product_title": "test product",
                        "price_min": "20.0",
                        "price_currency": "CNY",
                        "price_unit": "piece",
                    },
                    "usable_for_benchmark": True,
                    "invalid_reasons": [],
                }
            ],
            "imported_api_records": [],
            "public_benchmark_sample": [],
            "supplier_response_packets": [],
            "private_data_records": [],
            "private_customer_quote_history": [],
            "system_generated_records": [],
            "supplier_quote": None,
            "evidence_ids": ["pe_001"],
            "source_confidence": "persisted",
        },
        "evidence_ids": ["pe_001"],
        "mock_mode": False,
    }


class TestGiraffeDBContextRetriever:
    def _make_retriever(self, **kwargs) -> tuple[GiraffeDBContextRetriever, MagicMock]:
        client = MagicMock()
        client.create_gpm_context.return_value = _minimal_api_response()
        retriever = GiraffeDBContextRetriever(client=client, **kwargs)
        return retriever, client

    def test_retrieve_returns_context_bundle(self) -> None:
        retriever, _ = self._make_retriever()
        bundle = retriever.retrieve()
        assert isinstance(bundle, GPMContextBundle)

    def test_retrieve_calls_client_create_gpm_context(self) -> None:
        retriever, client = self._make_retriever()
        retriever.retrieve(rfq_id="rfq_001")
        client.create_gpm_context.assert_called_once()
        payload = client.create_gpm_context.call_args[0][0]
        assert payload["rfq_id"] == "rfq_001"

    def test_retrieve_default_include_private_is_false(self) -> None:
        retriever, client = self._make_retriever()
        retriever.retrieve()
        payload = client.create_gpm_context.call_args[0][0]
        assert payload["include_private_data"] is False

    def test_retrieve_override_include_private_data(self) -> None:
        retriever, client = self._make_retriever(include_private_data=False)
        retriever.retrieve(include_private_data=True)
        payload = client.create_gpm_context.call_args[0][0]
        assert payload["include_private_data"] is True

    def test_retrieve_client_error_propagates(self) -> None:
        client = MagicMock()
        client.create_gpm_context.side_effect = GiraffeDBClientError("service unreachable")
        retriever = GiraffeDBContextRetriever(client=client)
        with pytest.raises(GiraffeDBClientError, match="service unreachable"):
            retriever.retrieve()

    def test_retrieve_uses_default_tenant_id(self) -> None:
        retriever, client = self._make_retriever(default_tenant_id="tenant_default")
        retriever.retrieve()
        payload = client.create_gpm_context.call_args[0][0]
        assert payload["tenant_id"] == "tenant_default"

    def test_retrieve_forwards_evidence_ids(self) -> None:
        retriever, client = self._make_retriever()
        retriever.retrieve(evidence_ids=["ev_001", "ev_002"])
        payload = client.create_gpm_context.call_args[0][0]
        assert payload["evidence_ids"] == ["ev_001", "ev_002"]

    def test_build_gpm_context_is_alias_for_retrieve(self) -> None:
        retriever, client = self._make_retriever()
        bundle = retriever.build_gpm_context(rfq_id="rfq_001", include_private_data=False)
        assert isinstance(bundle, GPMContextBundle)
        payload = client.create_gpm_context.call_args[0][0]
        assert payload["rfq_id"] == "rfq_001"

    def test_retrieve_none_include_private_uses_constructor_default_true(self) -> None:
        retriever, client = self._make_retriever(include_private_data=True)
        retriever.retrieve(include_private_data=None)
        payload = client.create_gpm_context.call_args[0][0]
        assert payload["include_private_data"] is True

    def test_retrieve_explicit_false_overrides_constructor_default_true(self) -> None:
        retriever, client = self._make_retriever(include_private_data=True)
        retriever.retrieve(include_private_data=False)
        payload = client.create_gpm_context.call_args[0][0]
        assert payload["include_private_data"] is False
