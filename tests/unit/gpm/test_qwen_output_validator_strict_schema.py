"""Strict schema tests for QwenOutputValidator (Session D requirements)."""
from __future__ import annotations

import pytest

from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.validators.qwen_output_validator import QwenOutputValidator, QwenOutputValidationError


def _make_bundle() -> GPMContextBundle:
    return GPMContextBundle(
        bundle_id="b_strict",
        data_mode="mock",
        requirement={"product": "men cotton shirt"},
        evidence=[
            GPMEvidenceReference(id="ev_001", source_type="api_sample", source_id="ev_001"),
            GPMEvidenceReference(id="ev_002", source_type="api_sample", source_id="ev_002"),
        ],
    )


def _canonical_output() -> dict:
    return {
        "normalized_product_type": "men_cotton_shirt",
        "normalized_material": "cotton",
        "normalized_process_tags": ["oem_odm"],
        "is_comparable": True,
        "comparability_score": 0.85,
        "detected_mismatch_flags": [],
        "missing_fields": [],
        "risk_explanation": "",
        "evidence_ids": ["ev_001"],
        "reason": "Good match.",
        "confidence": "high",
        "human_approval_required": True,
    }


@pytest.fixture
def validator() -> QwenOutputValidator:
    return QwenOutputValidator()


@pytest.fixture
def bundle() -> GPMContextBundle:
    return _make_bundle()


def test_validator_accepts_canonical_qwen_output(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    validator.validate(_canonical_output(), bundle)


def test_validator_requires_human_approval_present(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    del out["human_approval_required"]
    with pytest.raises(QwenOutputValidationError, match="missing required keys"):
        validator.validate(out, bundle)


def test_validator_requires_human_approval_true(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["human_approval_required"] = False
    with pytest.raises(QwenOutputValidationError, match="human_approval_required"):
        validator.validate(out, bundle)


def test_validator_rejects_unknown_evidence_id(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["evidence_ids"] = ["ev_hallucinated_999"]
    with pytest.raises(QwenOutputValidationError, match="unknown evidence_id"):
        validator.validate(out, bundle)


def test_validator_rejects_price_field(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["price"] = 38.5
    with pytest.raises(QwenOutputValidationError, match="price"):
        validator.validate(out, bundle)


def test_validator_rejects_unit_price_field(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["unit_price"] = 38.5
    with pytest.raises(QwenOutputValidationError, match="unit_price"):
        validator.validate(out, bundle)


def test_validator_rejects_moq_field(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["moq"] = 1000
    with pytest.raises(QwenOutputValidationError, match="moq"):
        validator.validate(out, bundle)


def test_validator_rejects_auto_dispatch_instruction(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["reason"] = "dispatch quote to buyer for processing"
    with pytest.raises(QwenOutputValidationError, match="forbidden instruction"):
        validator.validate(out, bundle)


def test_validator_rejects_send_quote_key(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["send_quote"] = True
    with pytest.raises(QwenOutputValidationError, match="forbidden action key"):
        validator.validate(out, bundle)


def test_validator_rejects_dispatch_quote_key(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["dispatch_quote"] = True
    with pytest.raises(QwenOutputValidationError, match="forbidden action key"):
        validator.validate(out, bundle)


def test_validator_rejects_place_order_key(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["place_order"] = True
    with pytest.raises(QwenOutputValidationError, match="forbidden action key"):
        validator.validate(out, bundle)


def test_validator_rejects_make_payment_key(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["make_payment"] = True
    with pytest.raises(QwenOutputValidationError, match="forbidden action key"):
        validator.validate(out, bundle)


def test_validator_rejects_auto_approve_key(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _canonical_output()
    out["auto_approve"] = True
    with pytest.raises(QwenOutputValidationError, match="forbidden action key"):
        validator.validate(out, bundle)
