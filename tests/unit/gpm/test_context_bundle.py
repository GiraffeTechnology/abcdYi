from __future__ import annotations

from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.context.evidence_reference import GPMEvidenceReference


def _make_bundle(evidence=None):
    ev = evidence or [
        GPMEvidenceReference(id="ev_001", source_type="api_sample", source_id="s1"),
        GPMEvidenceReference(id="ev_002", source_type="api_sample", source_id="s2"),
    ]
    return GPMContextBundle(
        bundle_id="bundle_test_001",
        data_mode="mock",
        requirement={"product_type": "shirt", "quantity": 100},
        evidence=ev,
    )


def test_bundle_creation():
    bundle = _make_bundle()
    assert bundle.bundle_id == "bundle_test_001"
    assert bundle.data_mode == "mock"


def test_evidence_ids():
    bundle = _make_bundle()
    ids = bundle.evidence_ids()
    assert "ev_001" in ids
    assert "ev_002" in ids
    assert len(ids) == 2


def test_get_evidence_found():
    bundle = _make_bundle()
    ev = bundle.get_evidence("ev_001")
    assert ev is not None
    assert ev.id == "ev_001"


def test_get_evidence_missing():
    bundle = _make_bundle()
    assert bundle.get_evidence("ev_999") is None


def test_to_prompt_payload_includes_evidence_ids():
    bundle = _make_bundle()
    payload = bundle.to_prompt_payload()
    assert "evidence_ids" in payload
    assert "ev_001" in payload["evidence_ids"]
    assert "ev_002" in payload["evidence_ids"]


def test_to_prompt_payload_no_secrets():
    ev = [
        GPMEvidenceReference(
            id="ev_001",
            source_type="api_sample",
            source_id="s1",
            payload_excerpt={"product_title": "Shirt", "price": "35.0"},
        )
    ]
    bundle = GPMContextBundle(
        bundle_id="b001",
        data_mode="mock",
        requirement={"product_type": "shirt"},
        evidence=ev,
    )
    payload_str = str(bundle.to_prompt_payload()).lower()
    assert "password" not in payload_str
    assert "api_key" not in payload_str
    assert "secret" not in payload_str


def test_to_prompt_payload_strips_credential_keys_from_requirement():
    bundle = GPMContextBundle(
        bundle_id="b002",
        data_mode="mock",
        requirement={"product_type": "shirt", "api_key": "SHOULD_BE_STRIPPED"},
    )
    payload = bundle.to_prompt_payload()
    assert "api_key" not in payload["requirement"]
    assert "SHOULD_BE_STRIPPED" not in str(payload)


def test_to_prompt_payload_max_items():
    evidence = [
        GPMEvidenceReference(id=f"ev_{i:03d}", source_type="api_sample", source_id=f"s{i}")
        for i in range(30)
    ]
    bundle = GPMContextBundle(
        bundle_id="b003",
        data_mode="mock",
        requirement={"product_type": "shirt"},
        evidence=evidence,
    )
    payload = bundle.to_prompt_payload(max_items=5)
    assert len(payload["evidence"]) <= 5
