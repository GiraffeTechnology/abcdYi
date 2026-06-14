"""Tests for logistics state mapper (logistics status → order execution state)."""
import pytest
from src.logistics.logistics_state_mapper import map_logistics_status_to_order_state
from src.merchandiser.merchandiser_state_machine import logistics_status_to_order_state


def test_delivered_maps_to_delivered_not_closed():
    result = map_logistics_status_to_order_state("delivered")
    assert result == "DELIVERED"
    assert result != "ORDER_CLOSED"


def test_in_transit_maps_correctly():
    assert map_logistics_status_to_order_state("in_transit") == "IN_TRANSIT"


def test_picked_up_maps_to_in_transit():
    assert map_logistics_status_to_order_state("picked_up") == "IN_TRANSIT"


def test_label_created_maps_to_handover():
    assert map_logistics_status_to_order_state("label_created") == "LOGISTICS_HANDOVER_RECEIVED"


def test_customs_maps_correctly():
    assert map_logistics_status_to_order_state("customs") == "CUSTOMS"


def test_out_for_delivery_maps_correctly():
    assert map_logistics_status_to_order_state("out_for_delivery") == "OUT_FOR_DELIVERY"


def test_exception_maps_correctly():
    assert map_logistics_status_to_order_state("exception") == "EXCEPTION_RAISED"


def test_unknown_maps_to_none():
    assert map_logistics_status_to_order_state("unknown") is None
    assert map_logistics_status_to_order_state("some_random_status") is None


def test_state_mapper_delegates_to_state_machine():
    for status in ["delivered", "in_transit", "customs", "out_for_delivery", "exception"]:
        mapper_result = map_logistics_status_to_order_state(status)
        state_machine_result = logistics_status_to_order_state(status)
        assert mapper_result == state_machine_result


def test_delivered_does_not_auto_close_order():
    state = map_logistics_status_to_order_state("delivered")
    assert state == "DELIVERED"
    assert "CLOSED" not in (state or "")
    assert "BUYER_SIGNOFF" not in (state or "")


def test_all_canonical_statuses_covered():
    canonical = ["label_created", "picked_up", "in_transit", "customs", "out_for_delivery", "delivered", "exception"]
    for status in canonical:
        result = map_logistics_status_to_order_state(status)
        assert result is not None or status == "unknown", f"Expected result for {status}"
