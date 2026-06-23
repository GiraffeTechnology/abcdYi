from __future__ import annotations

from datetime import datetime, timezone

from src.gpm.context.evidence_reference import GPMEvidenceReference


def test_basic_creation():
    ref = GPMEvidenceReference(
        id="ev_001",
        source_type="api_sample",
        source_id="sample_001",
    )
    assert ref.id == "ev_001"
    assert ref.source_type == "api_sample"
    assert ref.source_id == "sample_001"
    assert ref.usable_for_analysis is True
    assert ref.invalid_reasons == []


def test_full_fields():
    now = datetime.now(timezone.utc)
    ref = GPMEvidenceReference(
        id="ev_002",
        source_type="supplier_quote",
        source_id="quote_001",
        source_platform="1688",
        title="Men's Cotton Shirt",
        observed_at=now,
        payload_excerpt={"price": "35.0", "product_title": "Shirt"},
        raw_payload_hash="abc123",
        usable_for_analysis=True,
    )
    assert ref.source_platform == "1688"
    assert ref.title == "Men's Cotton Shirt"
    assert ref.observed_at == now
    assert ref.payload_excerpt["price"] == "35.0"


def test_unusable_evidence():
    ref = GPMEvidenceReference(
        id="ev_003",
        source_type="api_sample",
        source_id="sample_003",
        usable_for_analysis=False,
        invalid_reasons=["missing_price", "missing_moq"],
    )
    assert ref.usable_for_analysis is False
    assert "missing_price" in ref.invalid_reasons
    assert "missing_moq" in ref.invalid_reasons


def test_no_credentials_in_excerpt():
    ref = GPMEvidenceReference(
        id="ev_004",
        source_type="api_sample",
        source_id="s004",
        payload_excerpt={
            "product_title": "Cotton Shirt",
            "price": "35.0",
            "supplier_name": "Supplier A",
        },
    )
    payload_str = str(ref.payload_excerpt).lower()
    assert "password" not in payload_str
    assert "api_key" not in payload_str
    assert "secret" not in payload_str
