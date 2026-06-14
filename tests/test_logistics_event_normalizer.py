"""Tests for logistics event normalizer."""
import pytest
from src.logistics.logistics_event_normalizer import normalize_raw_status, compute_event_hash


def test_normalize_delivered_english():
    assert normalize_raw_status("delivered") == "delivered"
    assert normalize_raw_status("Delivered") == "delivered"
    assert normalize_raw_status("delivery successful") == "delivered"


def test_normalize_delivered_chinese():
    assert normalize_raw_status("已签收") == "delivered"
    assert normalize_raw_status("签收") == "delivered"


def test_normalize_in_transit():
    assert normalize_raw_status("in_transit") == "in_transit"
    assert normalize_raw_status("in transit") == "in_transit"
    assert normalize_raw_status("运输中") == "in_transit"
    assert normalize_raw_status("shipped") == "in_transit"


def test_normalize_label_created():
    assert normalize_raw_status("label_created") == "label_created"
    assert normalize_raw_status("label created") == "label_created"
    assert normalize_raw_status("已创建面单") == "label_created"
    assert normalize_raw_status("已下单") == "label_created"


def test_normalize_picked_up():
    assert normalize_raw_status("picked_up") == "picked_up"
    assert normalize_raw_status("picked up") == "picked_up"
    assert normalize_raw_status("已揽收") == "picked_up"


def test_normalize_out_for_delivery():
    assert normalize_raw_status("out_for_delivery") == "out_for_delivery"
    assert normalize_raw_status("out for delivery") == "out_for_delivery"
    assert normalize_raw_status("派送中") == "out_for_delivery"


def test_normalize_customs():
    assert normalize_raw_status("customs") == "customs"
    assert normalize_raw_status("清关") == "customs"
    assert normalize_raw_status("customs clearance") == "customs"


def test_normalize_exception():
    assert normalize_raw_status("exception") == "exception"
    assert normalize_raw_status("delivery exception") == "exception"
    assert normalize_raw_status("异常") == "exception"
    assert normalize_raw_status("failed") == "exception"


def test_normalize_unknown():
    assert normalize_raw_status("some_random_status_xyz") == "unknown"


def test_normalize_case_insensitive():
    assert normalize_raw_status("DELIVERED") == "delivered"
    assert normalize_raw_status("IN_TRANSIT") == "in_transit"


def test_compute_event_hash_deterministic():
    h1 = compute_event_hash("SHIP-001", "mock", "SF123", "in_transit", "2025-01-01T00:00:00", "Shanghai", "In transit")
    h2 = compute_event_hash("SHIP-001", "mock", "SF123", "in_transit", "2025-01-01T00:00:00", "Shanghai", "In transit")
    assert h1 == h2


def test_compute_event_hash_different_inputs():
    h1 = compute_event_hash("SHIP-001", "mock", "SF123", "in_transit", "2025-01-01T00:00:00", "Shanghai", None)
    h2 = compute_event_hash("SHIP-001", "mock", "SF123", "delivered", "2025-01-01T00:00:00", "Shanghai", None)
    assert h1 != h2


def test_compute_event_hash_none_fields():
    h = compute_event_hash("SHIP-001", None, "SF123", "in_transit", None, None, None)
    assert isinstance(h, str)
    assert len(h) == 24


def test_compute_event_hash_length():
    h = compute_event_hash("SHIP-001", "mock", "SF123", "delivered", "2025-01-01", "BJ", "desc")
    assert len(h) == 24
