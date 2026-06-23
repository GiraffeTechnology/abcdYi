from __future__ import annotations

import pytest

from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.validators.context_bundle_validator import (
    validate_context_bundle,
    ContextBundleValidationError,
)


def _valid_bundle(**overrides):
    kwargs = dict(
        bundle_id="b001",
        data_mode="mock",
        requirement={"product_type": "shirt"},
        evidence=[
            GPMEvidenceReference(id="ev_001", source_type="api_sample", source_id="s1"),
        ],
    )
    kwargs.update(overrides)
    return GPMContextBundle(**kwargs)


def test_valid_bundle_passes():
    validate_context_bundle(_valid_bundle())


def test_rejects_empty_bundle_id():
    bundle = _valid_bundle(bundle_id="")
    with pytest.raises(ContextBundleValidationError, match="bundle_id"):
        validate_context_bundle(bundle)


def test_rejects_invalid_data_mode():
    bundle = _valid_bundle(data_mode="live")  # type: ignore
    with pytest.raises(ContextBundleValidationError, match="data_mode"):
        validate_context_bundle(bundle)


def test_accepts_all_valid_data_modes():
    for mode in ("public", "private", "mixed", "mock"):
        validate_context_bundle(_valid_bundle(data_mode=mode))


def test_rejects_duplicate_evidence_ids():
    evidence = [
        GPMEvidenceReference(id="ev_001", source_type="api_sample", source_id="s1"),
        GPMEvidenceReference(id="ev_001", source_type="api_sample", source_id="s2"),
    ]
    bundle = _valid_bundle(evidence=evidence)
    with pytest.raises(ContextBundleValidationError, match="unique"):
        validate_context_bundle(bundle)


def test_rejects_empty_requirement():
    bundle = _valid_bundle(requirement={})
    with pytest.raises(ContextBundleValidationError, match="requirement"):
        validate_context_bundle(bundle)


def test_rejects_credential_key_in_requirement():
    bundle = _valid_bundle(
        requirement={"product_type": "shirt", "api_key": "ABCDEFGH"}
    )
    with pytest.raises(ContextBundleValidationError, match="credential"):
        validate_context_bundle(bundle)


def test_rejects_credential_key_in_supplier_quote():
    bundle = _valid_bundle(
        supplier_quote={"price": "38.5", "password": "hunter2"}
    )
    with pytest.raises(ContextBundleValidationError, match="credential"):
        validate_context_bundle(bundle)


def test_rejects_credential_key_in_evidence_excerpt():
    ev = [
        GPMEvidenceReference(
            id="ev_001",
            source_type="api_sample",
            source_id="s1",
            payload_excerpt={"price": "35.0", "token": "secret_token"},
        )
    ]
    bundle = _valid_bundle(evidence=ev)
    with pytest.raises(ContextBundleValidationError, match="credential"):
        validate_context_bundle(bundle)
