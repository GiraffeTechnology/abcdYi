"""Tests for GPMContextBundle."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.context.gpm_context_bundle import GPMContextBundle


def _make_evidence(id: str, usable: bool = True) -> GPMEvidenceReference:
    return GPMEvidenceReference(
        id=id,
        source_type="api_sample",
        source_id=id,
        usable_for_analysis=usable,
        payload_excerpt={"price_min": "30", "price_currency": "CNY"},
    )


def _make_bundle(evidence: list[GPMEvidenceReference] | None = None) -> GPMContextBundle:
    return GPMContextBundle(
        bundle_id="bundle_test_001",
        data_mode="mock",
        requirement={"product": "men cotton shirt", "quantity": 10000},
        evidence=evidence or [],
    )


def test_bundle_creation_defaults() -> None:
    bundle = _make_bundle()
    assert bundle.bundle_id == "bundle_test_001"
    assert bundle.data_mode == "mock"
    assert bundle.tenant_id is None
    assert bundle.project_id is None


def test_evidence_ids_returns_set() -> None:
    ev = [_make_evidence("ev_a"), _make_evidence("ev_b")]
    bundle = _make_bundle(evidence=ev)
    assert bundle.evidence_ids() == {"ev_a", "ev_b"}


def test_get_evidence_found() -> None:
    ev = [_make_evidence("ev_a"), _make_evidence("ev_b")]
    bundle = _make_bundle(evidence=ev)
    result = bundle.get_evidence("ev_a")
    assert result is not None
    assert result.id == "ev_a"


def test_get_evidence_not_found() -> None:
    bundle = _make_bundle()
    assert bundle.get_evidence("nonexistent") is None


def test_to_prompt_payload_includes_evidence_ids() -> None:
    ev = [_make_evidence("ev_x"), _make_evidence("ev_y")]
    bundle = _make_bundle(evidence=ev)
    payload = bundle.to_prompt_payload()
    assert "ev_x" in payload["evidence_ids"]
    assert "ev_y" in payload["evidence_ids"]


def test_to_prompt_payload_includes_requirement() -> None:
    bundle = _make_bundle()
    payload = bundle.to_prompt_payload()
    assert payload["requirement"]["product"] == "men cotton shirt"


def test_to_prompt_payload_no_credentials() -> None:
    ev = [GPMEvidenceReference(
        id="ev_cred",
        source_type="api_sample",
        source_id="s1",
        payload_excerpt={"price_min": "30", "password": "secret123"},
    )]
    bundle = _make_bundle(evidence=ev)
    payload = bundle.to_prompt_payload()
    for entry in payload.get("evidence", []):
        excerpt = entry.get("payload_excerpt", {})
        assert "password" not in excerpt


def test_to_prompt_payload_max_items_respected() -> None:
    ev = [_make_evidence(f"ev_{i:03d}") for i in range(30)]
    bundle = _make_bundle(evidence=ev)
    payload = bundle.to_prompt_payload(max_items=5)
    assert len(payload["evidence_ids"]) <= 5


def test_to_prompt_payload_only_usable_evidence() -> None:
    ev = [_make_evidence("ev_good", usable=True), _make_evidence("ev_bad", usable=False)]
    bundle = _make_bundle(evidence=ev)
    payload = bundle.to_prompt_payload()
    # Only usable evidence should appear in the payload evidence list
    assert "ev_good" in payload["evidence_ids"]
    assert "ev_bad" not in payload["evidence_ids"]


def test_bundle_id_not_empty() -> None:
    bundle = _make_bundle()
    assert bundle.bundle_id


def test_create_classmethod() -> None:
    bundle = GPMContextBundle.create(
        data_mode="mock",
        requirement={"product": "shirt"},
    )
    assert bundle.bundle_id
    assert bundle.data_mode == "mock"
