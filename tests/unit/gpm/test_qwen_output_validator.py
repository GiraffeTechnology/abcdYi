from __future__ import annotations

import pytest

from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.context.evidence_reference import GPMEvidenceReference
from src.gpm.validators.qwen_output_validator import (
    validate_qwen_output,
    QwenOutputValidationError,
)


def _make_context(ev_ids=("ev_001", "ev_002")):
    return GPMContextBundle(
        bundle_id="b001",
        data_mode="mock",
        requirement={"product_type": "shirt"},
        evidence=[
            GPMEvidenceReference(id=eid, source_type="api_sample", source_id=f"s{i}")
            for i, eid in enumerate(ev_ids)
        ],
    )


def _valid_output(evidence_ids=("ev_001",)):
    return {
        "normalized_product_type": "men_cotton_shirt",
        "normalized_material": "cotton",
        "normalized_process_tags": ["oem"],
        "is_comparable": True,
        "comparability_score": 0.85,
        "detected_mismatch_flags": [],
        "evidence_ids": list(evidence_ids),
        "reason": "Good match.",
        "confidence": "high",
    }


def test_valid_output_passes():
    ctx = _make_context()
    validate_qwen_output(_valid_output(["ev_001"]), ctx)


def test_rejects_non_dict():
    ctx = _make_context()
    with pytest.raises(QwenOutputValidationError, match="JSON object"):
        validate_qwen_output("not a dict", ctx)


def test_rejects_missing_required_keys():
    ctx = _make_context()
    incomplete = {"normalized_product_type": "shirt"}
    with pytest.raises(QwenOutputValidationError, match="missing required keys"):
        validate_qwen_output(incomplete, ctx)


def test_rejects_score_out_of_range_high():
    ctx = _make_context()
    out = _valid_output(["ev_001"])
    out["comparability_score"] = 1.5
    with pytest.raises(QwenOutputValidationError, match="between 0 and 1"):
        validate_qwen_output(out, ctx)


def test_rejects_score_out_of_range_low():
    ctx = _make_context()
    out = _valid_output(["ev_001"])
    out["comparability_score"] = -0.1
    with pytest.raises(QwenOutputValidationError, match="between 0 and 1"):
        validate_qwen_output(out, ctx)


def test_rejects_non_numeric_score():
    ctx = _make_context()
    out = _valid_output(["ev_001"])
    out["comparability_score"] = "high"
    with pytest.raises(QwenOutputValidationError, match="numeric"):
        validate_qwen_output(out, ctx)


def test_rejects_unknown_evidence_ids():
    ctx = _make_context(ev_ids=("ev_001", "ev_002"))
    out = _valid_output(["ev_999"])
    with pytest.raises(QwenOutputValidationError, match="unknown evidence IDs"):
        validate_qwen_output(out, ctx)


def test_rejects_invented_price_field():
    ctx = _make_context()
    out = _valid_output(["ev_001"])
    out["invented_price"] = "99.99"
    with pytest.raises(QwenOutputValidationError, match="invented_price"):
        validate_qwen_output(out, ctx)


def test_rejects_invented_moq_field():
    ctx = _make_context()
    out = _valid_output(["ev_001"])
    out["invented_moq"] = 500
    with pytest.raises(QwenOutputValidationError, match="invented_moq"):
        validate_qwen_output(out, ctx)


def test_rejects_dispatch_buyer_quote_true():
    ctx = _make_context()
    out = _valid_output(["ev_001"])
    out["dispatch_buyer_quote"] = True
    with pytest.raises(QwenOutputValidationError, match="dispatch_buyer_quote"):
        validate_qwen_output(out, ctx)


def test_rejects_approve_order_true():
    ctx = _make_context()
    out = _valid_output(["ev_001"])
    out["approve_order"] = True
    with pytest.raises(QwenOutputValidationError, match="approve_order"):
        validate_qwen_output(out, ctx)


def test_empty_evidence_ids_accepted():
    ctx = _make_context()
    out = _valid_output([])
    validate_qwen_output(out, ctx)
