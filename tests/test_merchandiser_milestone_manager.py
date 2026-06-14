"""Tests for merchandiser milestone manager."""
import pytest
from src.merchandiser.milestone_manager import (
    create_milestones, get_milestone, get_milestones_for_project,
    request_milestone_media, upload_milestone_evidence,
    confirm_milestone, reject_milestone,
    find_next_pending_milestone, find_milestone_by_type, update_milestone_status,
)


_PROJECT = "test-mm-proj-01"
_SUP = "sup-mm-001"


def test_create_milestones_apparel():
    milestones = create_milestones(
        project_id=_PROJECT,
        category="apparel",
        assigned_actor_id=_SUP,
        order_id="OE-MM-001",
    )
    assert len(milestones) > 0
    types = [m.milestone_type for m in milestones]
    assert "material_arrival" in types
    assert "final_qc" in types
    assert "logistics_handover" in types


def test_create_milestones_cnc():
    proj = "test-mm-proj-cnc"
    milestones = create_milestones(
        project_id=proj,
        category="cnc_machining",
        assigned_actor_id=_SUP,
    )
    types = [m.milestone_type for m in milestones]
    assert "machining" in types


def test_milestones_ordered_by_sequence():
    proj = "test-mm-proj-02"
    milestones = create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    seqs = [m.sequence_no for m in milestones]
    assert seqs == sorted(seqs)


def test_get_milestone():
    proj = "test-mm-proj-03"
    milestones = create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    first = milestones[0]
    retrieved = get_milestone(first.milestone_id)
    assert retrieved.milestone_id == first.milestone_id
    assert retrieved.milestone_type == first.milestone_type


def test_get_milestone_not_found():
    with pytest.raises(FileNotFoundError):
        get_milestone("MILE-DOESNOTEXIST")


def test_request_milestone_media():
    proj = "test-mm-proj-04"
    milestones = create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    m = milestones[0]
    updated = request_milestone_media(m.milestone_id, proj)
    assert updated.status == "REQUESTED"


def test_upload_milestone_evidence():
    proj = "test-mm-proj-05"
    milestones = create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    m = milestones[0]
    updated = upload_milestone_evidence(m.milestone_id, proj, ["MEDIA-001", "MEDIA-002"])
    assert updated.status == "UPLOADED"
    assert "MEDIA-001" in updated.metadata.get("uploaded_media_ids", [])


def test_confirm_milestone():
    proj = "test-mm-proj-06"
    milestones = create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    m = milestones[0]
    confirmed = confirm_milestone(m.milestone_id, proj)
    assert confirmed.status == "CONFIRMED"


def test_reject_milestone():
    proj = "test-mm-proj-07"
    milestones = create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    m = milestones[0]
    rejected = reject_milestone(m.milestone_id, proj, reason="Photos too blurry")
    assert rejected.status == "REJECTED"
    assert "blurry" in rejected.metadata.get("rejection_reason", "")


def test_find_next_pending_milestone():
    proj = "test-mm-proj-08"
    milestones = create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    nxt = find_next_pending_milestone(proj)
    assert nxt is not None
    assert nxt.status == "PENDING"
    assert nxt.sequence_no == milestones[0].sequence_no


def test_find_milestone_by_type():
    proj = "test-mm-proj-09"
    create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    m = find_milestone_by_type(proj, "final_qc")
    assert m is not None
    assert m.milestone_type == "final_qc"


def test_find_milestone_by_type_missing():
    proj = "test-mm-proj-10"
    create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    result = find_milestone_by_type(proj, "nonexistent_type")
    assert result is None


def test_update_milestone_status():
    proj = "test-mm-proj-11"
    milestones = create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    m = milestones[0]
    updated = update_milestone_status(
        milestone_id=m.milestone_id,
        project_id=proj,
        status="REQUESTED",
        metadata={"note": "requested by engine"},
    )
    assert updated.status == "REQUESTED"
    assert updated.metadata.get("note") == "requested by engine"


def test_get_milestones_for_project():
    proj = "test-mm-proj-12"
    create_milestones(project_id=proj, category="apparel", assigned_actor_id=_SUP)
    all_m = get_milestones_for_project(proj)
    assert len(all_m) > 0
    assert all(m.project_id == proj for m in all_m)
