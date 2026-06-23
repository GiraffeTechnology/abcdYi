"""Tests for GPMEvidenceReference."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.gpm.context.evidence_reference import GPMEvidenceReference


def _make_ref(**kwargs: object) -> GPMEvidenceReference:
    defaults = dict(
        id="ev_001",
        source_type="api_sample",
        source_id="sample_001",
    )
    defaults.update(kwargs)
    return GPMEvidenceReference(**defaults)  # type: ignore[arg-type]


def test_minimal_creation() -> None:
    ref = _make_ref()
    assert ref.id == "ev_001"
    assert ref.source_type == "api_sample"
    assert ref.usable_for_analysis is True
    assert ref.invalid_reasons == []


def test_unusable_evidence_carries_reasons() -> None:
    ref = _make_ref(usable_for_analysis=False, invalid_reasons=["missing_price"])
    assert not ref.usable_for_analysis
    assert "missing_price" in ref.invalid_reasons


def test_optional_fields_default_to_none() -> None:
    ref = _make_ref()
    assert ref.source_platform is None
    assert ref.title is None
    assert ref.observed_at is None
    assert ref.payload_excerpt is None
    assert ref.raw_payload_hash is None


def test_payload_excerpt_stored() -> None:
    excerpt = {"price_min": "28.00", "price_currency": "CNY"}
    ref = _make_ref(payload_excerpt=excerpt)
    assert ref.payload_excerpt == excerpt


def test_all_source_types() -> None:
    for source_type in ("api_sample", "supplier_quote", "historical_order", "private_record", "manual_fixture"):
        ref = _make_ref(source_type=source_type)
        assert ref.source_type == source_type
