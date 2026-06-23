"""Tests for ContextBundleValidator."""
from __future__ import annotations

import pytest

from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.validators.context_bundle_validator import ContextBundleValidator, ContextBundleValidationError


def _make_bundle(**kwargs: object) -> GPMContextBundle:
    defaults = dict(
        bundle_id="b_test",
        data_mode="mock",
        requirement={"product": "shirt", "quantity": 1000},
        evidence=[],
    )
    defaults.update(kwargs)
    return GPMContextBundle(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def validator() -> ContextBundleValidator:
    return ContextBundleValidator()


def test_valid_bundle_passes(validator: ContextBundleValidator) -> None:
    bundle = _make_bundle()
    validator.validate(bundle)


def test_empty_bundle_id_rejected(validator: ContextBundleValidator) -> None:
    bundle = _make_bundle(bundle_id="")
    with pytest.raises(ContextBundleValidationError, match="bundle_id"):
        validator.validate(bundle)


def test_invalid_data_mode_rejected(validator: ContextBundleValidator) -> None:
    bundle = _make_bundle(data_mode="unknown_mode")
    with pytest.raises(ContextBundleValidationError, match="data_mode"):
        validator.validate(bundle)


def test_all_valid_data_modes(validator: ContextBundleValidator) -> None:
    for mode in ("public", "private", "mixed", "mock"):
        bundle = _make_bundle(data_mode=mode)
        validator.validate(bundle)


def test_duplicate_evidence_ids_rejected(validator: ContextBundleValidator) -> None:
    ev = [
        GPMEvidenceReference(id="ev_dup", source_type="api_sample", source_id="s1"),
        GPMEvidenceReference(id="ev_dup", source_type="api_sample", source_id="s2"),
    ]
    bundle = _make_bundle(evidence=ev)
    with pytest.raises(ContextBundleValidationError, match="unique"):
        validator.validate(bundle)


def test_empty_requirement_rejected(validator: ContextBundleValidator) -> None:
    bundle = _make_bundle(requirement={})
    with pytest.raises(ContextBundleValidationError, match="requirement"):
        validator.validate(bundle)


def test_credential_in_requirement_rejected(validator: ContextBundleValidator) -> None:
    bundle = _make_bundle(requirement={"product": "shirt", "api_key": "secret123"})
    with pytest.raises(ContextBundleValidationError, match="Credential-looking"):
        validator.validate(bundle)


def test_credential_in_supplier_quote_rejected(validator: ContextBundleValidator) -> None:
    bundle = _make_bundle(supplier_quote={"unit_price": 38.5, "token": "bearer_abc"})
    with pytest.raises(ContextBundleValidationError, match="Credential-looking"):
        validator.validate(bundle)


def test_credential_in_evidence_excerpt_rejected(validator: ContextBundleValidator) -> None:
    ev = [GPMEvidenceReference(
        id="ev_001", source_type="api_sample", source_id="s1",
        payload_excerpt={"price": "30", "password": "pw123"},
    )]
    bundle = _make_bundle(evidence=ev)
    with pytest.raises(ContextBundleValidationError, match="Credential-looking"):
        validator.validate(bundle)
