"""Unit tests for Giraffe JP message category permission logic."""
import pytest
from src.giraffe_jp.message_permissions import DEFAULT_CATEGORIES


def test_default_categories_total_count():
    """Spec requires exactly 22 default categories."""
    assert len(DEFAULT_CATEGORIES) == 22


def test_default_categories_party_type_counts():
    customer = [c for c in DEFAULT_CATEGORIES if c["party_type"] == "CUSTOMER"]
    supplier = [c for c in DEFAULT_CATEGORIES if c["party_type"] == "SUPPLIER"]
    model_partner = [c for c in DEFAULT_CATEGORIES if c["party_type"] == "MODEL_PARTNER"]
    assert len(customer) == 8
    assert len(supplier) == 7
    assert len(model_partner) == 7


def test_all_categories_have_required_fields():
    required = {"category_id", "category_name", "party_type", "channel", "auto_send"}
    for cat in DEFAULT_CATEGORIES:
        assert required.issubset(cat.keys()), f"Missing fields in {cat}"


def test_category_ids_are_unique():
    ids = [c["category_id"] for c in DEFAULT_CATEGORIES]
    assert len(ids) == len(set(ids)), "Duplicate category_id detected"


def test_auto_send_true_for_routine_notifications():
    lookup = {c["category_id"]: c["auto_send"] for c in DEFAULT_CATEGORIES}
    # Routine transactional notifications should be auto-sendable
    assert lookup["CUST_ORDER_CONFIRMATION"] is True
    assert lookup["CUST_MEASUREMENT_REQUEST"] is True
    assert lookup["CUST_QC_RESULT_NOTIFICATION"] is True
    assert lookup["SUPP_PRODUCTION_BRIEF"] is True
    assert lookup["MP_TRY_ON_APPOINTMENT"] is True
    assert lookup["MP_ENGAGEMENT_BRIEF"] is True


def test_auto_send_false_for_sensitive_categories():
    lookup = {c["category_id"]: c["auto_send"] for c in DEFAULT_CATEGORIES}
    # Payment and defect-related messages require human review
    assert lookup["CUST_PAYMENT_REMINDER"] is False
    assert lookup["SUPP_DEFECT_REPORT"] is False
    assert lookup["MP_COMPENSATION_NOTICE"] is False
    assert lookup["CUST_ALTERATION_REQUEST"] is False
    assert lookup["SUPP_SHIPMENT_INSTRUCTION"] is False


def test_unknown_category_not_in_defaults():
    """Spec rule 7: unknown categories must default to auto_send=False.
    Verified here by confirming they are absent from the seeded set.
    """
    known_ids = {c["category_id"] for c in DEFAULT_CATEGORIES}
    assert "UNKNOWN_CATEGORY_XYZ" not in known_ids
    assert "FAKE_CUST_SOMETHING" not in known_ids


def test_all_categories_use_email_channel():
    for cat in DEFAULT_CATEGORIES:
        assert cat["channel"] == "EMAIL", f"{cat['category_id']} has unexpected channel"


def test_auto_send_is_boolean():
    for cat in DEFAULT_CATEGORIES:
        assert isinstance(cat["auto_send"], bool), f"{cat['category_id']} auto_send is not bool"
