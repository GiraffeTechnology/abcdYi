"""Tests for merchandiser state machine."""
import pytest
from src.merchandiser.merchandiser_state_machine import (
    can_transition, assert_transition_allowed, transition_order_state,
    logistics_status_to_order_state,
)


def test_can_transition_valid():
    assert can_transition("ORDER_CONFIRMED", "SUPPLIER_ACCEPTANCE_PENDING") is True
    assert can_transition("DELIVERED", "BUYER_SIGNOFF_PENDING") is True
    assert can_transition("BUYER_SIGNED_OFF", "ORDER_CLOSED") is True
    assert can_transition("IN_TRANSIT", "DELIVERED") is True


def test_can_transition_invalid():
    assert can_transition("ORDER_CLOSED", "ORDER_CONFIRMED") is False
    assert can_transition("DELIVERED", "ORDER_CLOSED") is False
    assert can_transition("ORDER_CONFIRMED", "ORDER_CLOSED") is False


def test_delivered_must_pass_through_buyer_signoff():
    assert can_transition("DELIVERED", "BUYER_SIGNOFF_PENDING") is True
    assert can_transition("DELIVERED", "ORDER_CLOSED") is False
    assert can_transition("BUYER_SIGNED_OFF", "ORDER_CLOSED") is True


def test_assert_transition_allowed_valid():
    assert_transition_allowed("ORDER_CONFIRMED", "SUPPLIER_ACCEPTANCE_PENDING")
    assert_transition_allowed("BUYER_SIGNED_OFF", "ORDER_CLOSED")


def test_assert_transition_allowed_raises():
    with pytest.raises(ValueError, match="Invalid state transition"):
        assert_transition_allowed("ORDER_CLOSED", "ORDER_CONFIRMED")

    with pytest.raises(ValueError):
        assert_transition_allowed("DELIVERED", "ORDER_CLOSED")


def test_transition_order_state_logs():
    result = transition_order_state("proj-test-sm-01", "SUPPLIER_ACCEPTED", "supplier confirmed")
    assert result["to_state"] == "SUPPLIER_ACCEPTED"
    assert result["project_id"] == "proj-test-sm-01"


def test_transition_order_state_with_metadata():
    result = transition_order_state(
        "proj-test-sm-02", "IN_TRANSIT", "logistics picked up",
        plan_id="EXECPLAN-001", order_id="OE-001", actor_id="sup-001",
    )
    assert result["to_state"] == "IN_TRANSIT"


def test_logistics_to_order_state():
    assert logistics_status_to_order_state("delivered") == "DELIVERED"
    assert logistics_status_to_order_state("in_transit") == "IN_TRANSIT"
    assert logistics_status_to_order_state("customs") == "CUSTOMS"
    assert logistics_status_to_order_state("out_for_delivery") == "OUT_FOR_DELIVERY"
    assert logistics_status_to_order_state("exception") == "EXCEPTION_RAISED"
    assert logistics_status_to_order_state("label_created") == "LOGISTICS_HANDOVER_RECEIVED"
    assert logistics_status_to_order_state("picked_up") == "IN_TRANSIT"
    assert logistics_status_to_order_state("unknown_xyz") is None


def test_delivered_does_not_map_to_order_closed():
    result = logistics_status_to_order_state("delivered")
    assert result != "ORDER_CLOSED"
    assert result == "DELIVERED"


def test_exception_paths():
    assert can_transition("EXCEPTION_RAISED", "EXCEPTION_RESOLUTION_PENDING") is True
    assert can_transition("EXCEPTION_RESOLVED", "PRODUCTION_STARTED") is True
    assert can_transition("EXCEPTION_RAISED", "CANCELLED") is True


def test_cancelled_is_terminal():
    assert can_transition("CANCELLED", "ORDER_CONFIRMED") is False
    assert can_transition("CANCELLED", "EXCEPTION_RAISED") is False
    assert len([t for t in ["ORDER_CONFIRMED", "DELIVERED"] if can_transition("CANCELLED", t)]) == 0
