"""Tests for B-side merchandiser message templates and routing."""
import pytest
from src.merchandiser.message_templates import (
    B_MILESTONE_REVIEW, B_LOGISTICS_UPDATE, B_DELIVERY_SIGNOFF, B_EXCEPTION_OPTIONS, render,
)
from src.merchandiser.side_router import route_merchandiser_message, _build_b_side_message


def test_b_milestone_review_template():
    msg = render(B_MILESTONE_REVIEW, media_count=3, milestone_type="Final QC")
    assert "3" in msg
    assert "Final QC" in msg
    assert "Confirm" in msg


def test_b_logistics_update_template():
    msg = render(B_LOGISTICS_UPDATE, tracking_number="SF123456789", carrier_name="SF Express", normalized_status="in_transit")
    assert "SF123456789" in msg
    assert "SF Express" in msg
    assert "in_transit" in msg


def test_b_delivery_signoff_template():
    msg = render(B_DELIVERY_SIGNOFF, tracking_number="SF123456789")
    assert "SF123456789" in msg
    assert "delivered" in msg.lower()
    assert "Confirm received" in msg


def test_b_exception_options_template():
    msg = render(
        B_EXCEPTION_OPTIONS,
        exception_type="Material Shortage",
        options_text="A. Switch fabric\nB. Wait 2 weeks",
    )
    assert "Material Shortage" in msg
    assert "Switch fabric" in msg


def test_route_b_side_explicit():
    result = route_merchandiser_message(
        project_id="proj-b-001",
        actor_id="sup-001",
        event_or_task={"event_type": "milestone_review", "assigned_side": "B_SIDE"},
    )
    assert result["side"] == "B_SIDE"
    assert len(result["message"]) > 0


def test_route_b_side_buyer_keyword():
    result = route_merchandiser_message(
        project_id="proj-b-002",
        actor_id="sup-002",
        event_or_task={"event_type": "buyer_milestone_review", "assigned_side": "M_SIDE"},
    )
    assert result["side"] == "B_SIDE"


def test_route_m_side_explicit():
    result = route_merchandiser_message(
        project_id="proj-m-001",
        actor_id="sup-001",
        event_or_task={"event_type": "production_start", "assigned_side": "M_SIDE"},
    )
    assert result["side"] == "M_SIDE"


def test_build_b_side_material_delay():
    msg = _build_b_side_message("material_delay_reported", {"tracking_number": ""})
    assert "fabric" in msg.lower() or "delay" in msg.lower()


def test_build_b_side_milestone():
    msg = _build_b_side_message("milestone_update", {"milestone_type": "final_qc"})
    assert "milestone" in msg.lower() or "Final Qc" in msg or "confirm" in msg.lower()


def test_build_b_side_logistics():
    msg = _build_b_side_message("logistics_update", {"tracking_number": "SF9876543210"})
    assert "SF9876543210" in msg or "Tracking" in msg or "logistics" in msg.lower()


def test_build_b_side_fallback():
    msg = _build_b_side_message("unknown_event_xyz", {})
    assert len(msg) > 0


def test_render_with_extra_kwargs():
    msg = render(B_MILESTONE_REVIEW, media_count=1, milestone_type="Cutting")
    assert "Cutting" in msg
    assert "1" in msg
