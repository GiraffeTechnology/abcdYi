"""Tests for EvidenceReference (Pydantic) and GPMContextBundle helpers."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.gpm.context.evidence_reference import EvidenceReference, GPMEvidenceReference
from src.gpm.context.gpm_context_bundle import GPMContextBundle


# ── EvidenceReference (Pydantic) ─────────────────────────────────────────────

def test_evidence_reference_pydantic_creation() -> None:
    ref = EvidenceReference(
        evidence_id="ev_public_001",
        source_type="authorized_marketplace_api",
        visibility="public_benchmark",
        source_label="1688 mock",
    )
    assert ref.evidence_id == "ev_public_001"
    assert ref.source_type == "authorized_marketplace_api"
    assert ref.visibility == "public_benchmark"


def test_evidence_reference_pydantic_defaults() -> None:
    ref = EvidenceReference(
        evidence_id="ev_002",
        source_type="csv_import",
        visibility="tenant_private",
    )
    assert ref.source_label is None
    assert ref.observed_at is None
    assert ref.captured_at is None
    assert ref.payload == {}


def test_evidence_reference_no_qc_types() -> None:
    """EvidenceReference must not include QC-specific source types."""
    allowed = {
        "public_api", "authorized_marketplace_api", "csv_import", "excel_import",
        "private_erp", "private_supplier_quote", "private_historical_order",
        "supplier_email", "manual_upload", "system_generated_quote",
        "system_generated_order", "system_generated_execution_event",
    }
    forbidden_qc = {"qc_image", "qc_video", "qc_report", "qc_reference"}
    for ft in forbidden_qc:
        assert ft not in allowed


def test_evidence_reference_pydantic_serializable() -> None:
    ref = EvidenceReference(
        evidence_id="ev_ser",
        source_type="private_erp",
        visibility="tenant_private",
        payload={"price": "38.5", "currency": "CNY"},
    )
    d = ref.model_dump()
    assert d["evidence_id"] == "ev_ser"
    assert d["payload"]["price"] == "38.5"


# ── GPMContextBundle (existing dataclass) helpers ────────────────────────────

def _bundle_with_ev(*ev_ids: str) -> GPMContextBundle:
    from src.gpm.context.evidence_reference import GPMEvidenceReference
    ev = [GPMEvidenceReference(id=eid, source_type="api_sample", source_id=eid) for eid in ev_ids]
    return GPMContextBundle(
        bundle_id="b_test",
        data_mode="mock",
        requirement={"product": "shirt"},
        evidence=ev,
    )


def test_all_evidence_ids_collected() -> None:
    bundle = _bundle_with_ev("ev_001", "ev_002", "ev_003")
    assert bundle.evidence_ids() == {"ev_001", "ev_002", "ev_003"}


def test_to_prompt_context_includes_evidence_ids() -> None:
    bundle = _bundle_with_ev("ev_a", "ev_b")
    payload = bundle.to_prompt_payload()
    for eid in ("ev_a", "ev_b"):
        assert eid in payload["evidence_ids"]


def test_to_prompt_context_is_json_serializable() -> None:
    import json
    bundle = _bundle_with_ev("ev_001")
    payload = bundle.to_prompt_payload()
    # Must not raise
    json.dumps(payload, default=str)


def test_bundle_excludes_credentials_from_payload() -> None:
    from src.gpm.context.evidence_reference import GPMEvidenceReference
    ev = [GPMEvidenceReference(
        id="ev_cred", source_type="api_sample", source_id="s1",
        payload_excerpt={"price_min": "30", "token": "should_be_removed"},
    )]
    bundle = GPMContextBundle(
        bundle_id="b_cred", data_mode="mock",
        requirement={"product": "shirt"}, evidence=ev,
    )
    payload = bundle.to_prompt_payload()
    for entry in payload.get("evidence", []):
        assert "token" not in entry.get("payload_excerpt", {})
