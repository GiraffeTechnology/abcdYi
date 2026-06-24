"""Unit tests for GiraffeDBContextMapper."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.gpm.context.mappers.giraffe_db_context_mapper import (
    GiraffeDBContextMapper,
    InsufficientContextDataError,
)
from src.gpm.context.gpm_context_bundle import GPMContextBundle


def _pe(item_id: str, price_min: str = "25.0", extra_payload: dict | None = None) -> dict:
    payload = {
        "product_title": f"product {item_id}",
        "price_min": price_min,
        "price_currency": "CNY",
        "price_unit": "piece",
        "moq": "500",
        "material": "cotton",
        "source_platform": "mock_1688",
    }
    if extra_payload:
        payload.update(extra_payload)
    return {
        "id": item_id,
        "source_type": "public_api",
        "source_id": item_id,
        "source_platform": "mock_1688",
        "raw_payload_hash": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "payload": payload,
        "usable_for_benchmark": True,
        "invalid_reasons": [],
    }


def _private_record(item_id: str) -> dict:
    return {
        "id": item_id,
        "source_type": "private_erp",
        "source_id": item_id,
        "source_platform": "internal",
        "raw_payload_hash": None,
        "created_at": "2024-01-01T00:00:00+00:00",
        "payload": {"title": f"private record {item_id}"},
        "usable_for_analysis": True,
        "invalid_reasons": [],
    }


def _minimal_response(
    pricing_evidence: list | None = None,
    private_data: list | None = None,
    supplier_quote: dict | None = None,
) -> dict:
    return {
        "id": "ctx_test_001",
        "tenant_id": "tenant_001",
        "project_id": "project_001",
        "created_at": "2024-06-01T12:00:00+00:00",
        "pricing_context": {
            "rfq": {"id": "rfq_001", "product": "men's shirt", "quantity": 1000, "unit": "piece"},
            "pricing_evidence": pricing_evidence or [],
            "imported_api_records": [],
            "public_benchmark_sample": [],
            "supplier_response_packets": [],
            "private_data_records": private_data or [],
            "private_customer_quote_history": [],
            "system_generated_records": [],
            "supplier_quote": supplier_quote,
            "evidence_ids": [],
            "source_confidence": "persisted",
        },
        "evidence_ids": [],
        "mock_mode": False,
    }


class TestGiraffeDBContextMapperBasic:
    def test_map_returns_context_bundle(self) -> None:
        response = _minimal_response(pricing_evidence=[_pe("pe_001")])
        bundle = GiraffeDBContextMapper().map(response)
        assert isinstance(bundle, GPMContextBundle)

    def test_map_bundle_id_from_response(self) -> None:
        response = _minimal_response(pricing_evidence=[_pe("pe_001")])
        bundle = GiraffeDBContextMapper().map(response)
        assert bundle.bundle_id == "ctx_test_001"

    def test_map_tenant_and_project_ids(self) -> None:
        response = _minimal_response(pricing_evidence=[_pe("pe_001")])
        bundle = GiraffeDBContextMapper().map(response)
        assert bundle.tenant_id == "tenant_001"
        assert bundle.project_id == "project_001"

    def test_map_requirement_from_rfq(self) -> None:
        response = _minimal_response(pricing_evidence=[_pe("pe_001")])
        bundle = GiraffeDBContextMapper().map(response)
        assert bundle.requirement["product"] == "men's shirt"
        assert bundle.requirement["quantity"] == 1000

    def test_map_evidence_list_populated(self) -> None:
        evidence = [_pe("pe_001"), _pe("pe_002")]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        assert len(bundle.evidence) == 2
        assert {e.id for e in bundle.evidence} == {"pe_001", "pe_002"}

    def test_map_price_samples_populated(self) -> None:
        evidence = [_pe("pe_001", price_min="30.5"), _pe("pe_002", price_min="32.0")]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        assert len(bundle.price_samples) == 2

    def test_map_price_min_converted_to_decimal(self) -> None:
        response = _minimal_response(pricing_evidence=[_pe("pe_001", price_min="24.5")])
        bundle = GiraffeDBContextMapper().map(response)
        sample = bundle.price_samples[0]
        assert isinstance(sample["price_min"], Decimal)
        assert sample["price_min"] == Decimal("24.5")

    def test_map_moq_converted_to_decimal(self) -> None:
        response = _minimal_response(pricing_evidence=[_pe("pe_001")])
        bundle = GiraffeDBContextMapper().map(response)
        sample = bundle.price_samples[0]
        assert isinstance(sample["moq"], Decimal)
        assert sample["moq"] == Decimal("500")


class TestGiraffeDBContextMapperDataMode:
    def test_public_only_gives_public_data_mode(self) -> None:
        response = _minimal_response(pricing_evidence=[_pe("pe_001")])
        bundle = GiraffeDBContextMapper().map(response, include_private_data=False)
        assert bundle.data_mode == "public"

    def test_private_only_gives_private_data_mode(self) -> None:
        response = _minimal_response(private_data=[_private_record("priv_001")])
        bundle = GiraffeDBContextMapper().map(response, include_private_data=True)
        assert bundle.data_mode == "private"

    def test_mixed_gives_mixed_data_mode(self) -> None:
        response = _minimal_response(
            pricing_evidence=[_pe("pe_001")],
            private_data=[_private_record("priv_001")],
        )
        bundle = GiraffeDBContextMapper().map(response, include_private_data=True)
        assert bundle.data_mode == "mixed"

    def test_private_excluded_when_include_private_false(self) -> None:
        response = _minimal_response(
            pricing_evidence=[_pe("pe_001")],
            private_data=[_private_record("priv_001")],
        )
        bundle = GiraffeDBContextMapper().map(response, include_private_data=False)
        assert bundle.data_mode == "public"
        ids = {e.id for e in bundle.evidence}
        assert "priv_001" not in ids


class TestGiraffeDBContextMapperCredentials:
    def test_credential_keys_stripped_from_payload(self) -> None:
        evidence = [_pe("pe_001", extra_payload={"token": "secret123", "api_key": "key456"})]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        excerpt = bundle.evidence[0].payload_excerpt or {}
        assert "token" not in excerpt
        assert "api_key" not in excerpt

    def test_non_credential_keys_preserved(self) -> None:
        evidence = [_pe("pe_001", extra_payload={"color": "white", "weight": "200g"})]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        excerpt = bundle.evidence[0].payload_excerpt or {}
        assert excerpt.get("color") == "white"
        assert excerpt.get("weight") == "200g"


class TestGiraffeDBContextMapperEdgeCases:
    def test_empty_response_raises_insufficient_context(self) -> None:
        response = _minimal_response()  # no pricing_evidence, no private_data
        with pytest.raises(InsufficientContextDataError):
            GiraffeDBContextMapper().map(response)

    def test_deduplication_across_lists(self) -> None:
        # pe_001 appears in both pricing_evidence and public_benchmark_sample
        item = _pe("pe_001")
        response = _minimal_response(pricing_evidence=[item])
        response["pricing_context"]["public_benchmark_sample"] = [item]
        bundle = GiraffeDBContextMapper().map(response)
        ids = [e.id for e in bundle.evidence]
        assert ids.count("pe_001") == 1
        assert len([s for s in bundle.price_samples if s["id"] == "pe_001"]) == 1

    def test_supplier_quote_mapped(self) -> None:
        sq = {"unit_price": "38.5", "currency": "CNY", "moq": "1000"}
        response = _minimal_response(pricing_evidence=[_pe("pe_001")], supplier_quote=sq)
        bundle = GiraffeDBContextMapper().map(response)
        assert bundle.supplier_quote is not None
        assert isinstance(bundle.supplier_quote["unit_price"], Decimal)
        assert bundle.supplier_quote["unit_price"] == Decimal("38.5")

    def test_created_at_parsed_from_response(self) -> None:
        response = _minimal_response(pricing_evidence=[_pe("pe_001")])
        bundle = GiraffeDBContextMapper().map(response)
        assert bundle.created_at.year == 2024
        assert bundle.created_at.month == 6


class TestGiraffeDBContextMapperExtendedCredentialStripping:
    def test_access_token_stripped(self) -> None:
        evidence = [_pe("pe_001", extra_payload={"access_token": "tok_abc123"})]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        excerpt = bundle.evidence[0].payload_excerpt or {}
        assert "access_token" not in excerpt

    def test_refresh_token_stripped(self) -> None:
        evidence = [_pe("pe_001", extra_payload={"refresh_token": "ref_xyz789"})]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        excerpt = bundle.evidence[0].payload_excerpt or {}
        assert "refresh_token" not in excerpt

    def test_api_token_stripped(self) -> None:
        evidence = [_pe("pe_001", extra_payload={"api_token": "apitok_000"})]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        excerpt = bundle.evidence[0].payload_excerpt or {}
        assert "api_token" not in excerpt

    def test_authorization_header_stripped(self) -> None:
        evidence = [_pe("pe_001", extra_payload={"authorization_header": "Bearer secret"})]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        excerpt = bundle.evidence[0].payload_excerpt or {}
        assert "authorization_header" not in excerpt

    def test_nested_api_key_in_sub_dict_stripped(self) -> None:
        nested = {"meta": {"api_key": "nested_secret", "region": "ap-east"}}
        evidence = [_pe("pe_001", extra_payload=nested)]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        excerpt = bundle.evidence[0].payload_excerpt or {}
        assert "api_key" not in excerpt.get("meta", {})
        assert excerpt.get("meta", {}).get("region") == "ap-east"

    def test_nested_access_token_in_list_stripped(self) -> None:
        nested = {"tags": [{"access_token": "tok_list", "name": "tag1"}]}
        evidence = [_pe("pe_001", extra_payload=nested)]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        excerpt = bundle.evidence[0].payload_excerpt or {}
        tag = excerpt.get("tags", [{}])[0]
        assert "access_token" not in tag
        assert tag.get("name") == "tag1"

    def test_prompt_payload_strips_credentials_recursively(self) -> None:
        nested = {"meta": {"client_secret": "cs_secret", "source": "api"}}
        evidence = [_pe("pe_001", extra_payload=nested)]
        response = _minimal_response(pricing_evidence=evidence)
        bundle = GiraffeDBContextMapper().map(response)
        prompt_payload = bundle.to_prompt_payload()
        for ev in prompt_payload.get("evidence", []):
            excerpt = ev.get("payload_excerpt") or {}
            assert "client_secret" not in excerpt.get("meta", {})
