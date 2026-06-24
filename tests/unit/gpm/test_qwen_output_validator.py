"""Tests for QwenOutputValidator."""
from __future__ import annotations

import pytest

from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.validators.qwen_output_validator import QwenOutputValidator, QwenOutputValidationError


def _make_bundle(evidence_ids: list[str] | None = None) -> GPMContextBundle:
    ev = [
        GPMEvidenceReference(id=eid, source_type="api_sample", source_id=eid)
        for eid in (evidence_ids or ["ev_001", "ev_002"])
    ]
    return GPMContextBundle(
        bundle_id="b_test",
        data_mode="mock",
        requirement={"product": "shirt"},
        evidence=ev,
    )


def _valid_output(evidence_ids: list[str] | None = None) -> dict:
    return {
        "normalized_product_type": "men_cotton_shirt",
        "normalized_material": "cotton",
        "normalized_process_tags": [],
        "is_comparable": True,
        "comparability_score": 0.85,
        "detected_mismatch_flags": [],
        "evidence_ids": evidence_ids or ["ev_001"],
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


def test_valid_output_passes(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    validator.validate(_valid_output(), bundle)


def test_non_dict_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    with pytest.raises(QwenOutputValidationError, match="JSON object"):
        validator.validate("not a dict", bundle)


def test_missing_required_key(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    del out["comparability_score"]
    with pytest.raises(QwenOutputValidationError, match="missing required keys"):
        validator.validate(out, bundle)


def test_missing_human_approval_key(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    del out["human_approval_required"]
    with pytest.raises(QwenOutputValidationError, match="missing required keys"):
        validator.validate(out, bundle)


def test_human_approval_false_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["human_approval_required"] = False
    with pytest.raises(QwenOutputValidationError, match="human_approval_required"):
        validator.validate(out, bundle)


def test_score_above_one_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["comparability_score"] = 1.5
    with pytest.raises(QwenOutputValidationError, match="comparability_score"):
        validator.validate(out, bundle)


def test_score_below_zero_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["comparability_score"] = -0.1
    with pytest.raises(QwenOutputValidationError, match="comparability_score"):
        validator.validate(out, bundle)


def test_unknown_evidence_id_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output(evidence_ids=["ev_999_unknown"])
    with pytest.raises(QwenOutputValidationError, match="unknown evidence_id"):
        validator.validate(out, bundle)


def test_invented_price_field_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["price"] = 38.5
    with pytest.raises(QwenOutputValidationError, match="price"):
        validator.validate(out, bundle)


def test_invented_moq_field_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["moq"] = 1000
    with pytest.raises(QwenOutputValidationError, match="moq"):
        validator.validate(out, bundle)


def test_order_instruction_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["reason"] = "place order now for best price"
    with pytest.raises(QwenOutputValidationError, match="forbidden instruction"):
        validator.validate(out, bundle)


def test_auto_dispatch_instruction_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["reason"] = "dispatch quote to buyer automatically"
    with pytest.raises(QwenOutputValidationError, match="forbidden instruction"):
        validator.validate(out, bundle)


def test_payment_instruction_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["reason"] = "make payment to supplier"
    with pytest.raises(QwenOutputValidationError, match="forbidden instruction"):
        validator.validate(out, bundle)


def test_non_numeric_score_rejected(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["comparability_score"] = "high"
    with pytest.raises(QwenOutputValidationError, match="numeric"):
        validator.validate(out, bundle)


def test_empty_evidence_ids_list_is_valid(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output(evidence_ids=[])
    validator.validate(out, bundle)


def test_forbidden_key_send_quote(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["send_quote"] = True
    with pytest.raises(QwenOutputValidationError, match="forbidden action key"):
        validator.validate(out, bundle)


def test_forbidden_key_place_order(validator: QwenOutputValidator, bundle: GPMContextBundle) -> None:
    out = _valid_output()
    out["place_order"] = True
    with pytest.raises(QwenOutputValidationError, match="forbidden action key"):
        validator.validate(out, bundle)
