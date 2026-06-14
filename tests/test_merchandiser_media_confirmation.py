"""Tests for merchandiser media evidence / confirmation."""
import pytest
from src.merchandiser.media_confirmation import (
    upload_media_evidence, get_media_for_milestone,
    check_media_completeness, mark_media_buyer_confirmed, mark_media_buyer_rejected,
)


_PROJECT = "test-mc-proj-01"
_SUPPLIER = "sup-mc-001"
_BUYER = "buy-mc-001"
_MILESTONE = "MILE-TESTMC001"


def test_upload_media_evidence_single():
    evidences = upload_media_evidence(
        project_id=_PROJECT,
        milestone_id=_MILESTONE,
        uploaded_by_actor_id=_SUPPLIER,
        media_type="image",
        count=1,
    )
    assert len(evidences) == 1
    assert evidences[0].media_id.startswith("MEDIA-")
    assert evidences[0].milestone_id == _MILESTONE
    assert evidences[0].media_type == "image"
    assert evidences[0].buyer_review_status == "pending"


def test_upload_media_evidence_multiple():
    milestone = "MILE-TESTMC002"
    evidences = upload_media_evidence(
        project_id=_PROJECT,
        milestone_id=milestone,
        uploaded_by_actor_id=_SUPPLIER,
        media_type="image",
        count=3,
    )
    assert len(evidences) == 3
    ids = [e.media_id for e in evidences]
    assert len(set(ids)) == 3


def test_upload_shipping_label_not_required_review():
    milestone = "MILE-TESTMC003"
    evidences = upload_media_evidence(
        project_id=_PROJECT,
        milestone_id=milestone,
        uploaded_by_actor_id=_SUPPLIER,
        media_type="shipping_label",
        count=1,
    )
    assert evidences[0].buyer_review_status == "not_required"


def test_get_media_for_milestone():
    milestone = "MILE-TESTMC004"
    upload_media_evidence(project_id=_PROJECT, milestone_id=milestone, uploaded_by_actor_id=_SUPPLIER, count=2)
    media = get_media_for_milestone(milestone)
    assert len(media) >= 2
    assert all(m.milestone_id == milestone for m in media)


def test_get_media_for_milestone_empty():
    media = get_media_for_milestone("MILE-NONEXISTENT-XYZ")
    assert media == []


def test_check_media_completeness_with_media():
    milestone = "MILE-TESTMC005"
    upload_media_evidence(project_id=_PROJECT, milestone_id=milestone, uploaded_by_actor_id=_SUPPLIER, count=1)
    result = check_media_completeness(_PROJECT, milestone)
    assert result["complete"] is True
    assert result["count"] >= 1


def test_check_media_completeness_empty():
    result = check_media_completeness(_PROJECT, "MILE-EMPTY-XYZ")
    assert result["complete"] is False
    assert result["count"] == 0


def test_mark_media_buyer_confirmed():
    milestone = "MILE-TESTMC006"
    upload_media_evidence(project_id=_PROJECT, milestone_id=milestone, uploaded_by_actor_id=_SUPPLIER, count=2)
    result = mark_media_buyer_confirmed(_PROJECT, milestone, _BUYER)
    assert result["confirmed_count"] >= 1
    assert result["milestone_id"] == milestone


def test_mark_media_buyer_rejected():
    milestone = "MILE-TESTMC007"
    upload_media_evidence(project_id=_PROJECT, milestone_id=milestone, uploaded_by_actor_id=_SUPPLIER, count=1)
    result = mark_media_buyer_rejected(_PROJECT, milestone, _BUYER, reason="Angle unclear")
    assert result["rejected_count"] >= 1
    assert "reason" in result


def test_upload_document_type():
    milestone = "MILE-TESTMC008"
    evidences = upload_media_evidence(
        project_id=_PROJECT,
        milestone_id=milestone,
        uploaded_by_actor_id=_SUPPLIER,
        media_type="document",
        description="QC inspection report",
    )
    assert len(evidences) == 1
    assert evidences[0].media_type == "document"
    assert evidences[0].description == "QC inspection report"
