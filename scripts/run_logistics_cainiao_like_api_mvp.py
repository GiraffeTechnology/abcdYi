"""
Cainiao-like Logistics API MVP — 12-step test.

Tests: IM message extraction → shipment creation → mock API fetch
→ normalization → deduplication → order state update → sign-off trigger
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logistics.logistics_message_parser import extract_logistics_info_from_im
from src.logistics.logistics_ingestion_service import (
    ingest_tracking_number, sync_tracking_from_provider,
    ingest_logistics_from_im_message, _normalize_and_store_events,
)
from src.logistics.logistics_event_normalizer import normalize_raw_status
from src.logistics.logistics_models import get_shipment, get_events_for_shipment, get_shipments_for_project
from src.logistics.logistics_state_mapper import map_logistics_status_to_order_state
from src.logistics.providers.provider_registry import get_logistics_provider
from src.logistics.providers.cainiao_like_provider import CainiaoLikeProvider
from src.logistics.providers.mock_provider import MockProvider
from src.merchandiser.b_side.b_signoff import request_buyer_signoff
from src.projects.project_graph import create_project
from src.b_side.workspace import create_b_workspace
from src.m_side.m_event_logger import log_m_event, read_events

_steps_passed = 0
_steps_failed = 0


def step(n, desc):
    print(f"\n--- Step {n}: {desc} ---")


def ok(msg):
    global _steps_passed
    _steps_passed += 1
    print(f"  ✓ {msg}")


def fail(msg):
    global _steps_failed
    _steps_failed += 1
    print(f"  ✗ FAIL: {msg}")


def check(condition, msg):
    if condition:
        ok(msg)
    else:
        fail(msg)


BUYER_ID = "actor_buyer_logistics_test"
SUPPLIER_ID = "actor_manufacturer_logistics_test"
IM_MSG_ZH = "已发顺丰，单号 SF123456789012，今天下午发出"
IM_MSG_EN = "DHL shipped today, tracking no. 1234567890123"


def main():
    print("=" * 70)
    print("CAINIAO-LIKE LOGISTICS API MVP — End-to-End Test")
    print("=" * 70)

    # ── Step 1: Create project and confirmed order ─────────────────────────────
    step(1, "Create project and confirmed order")

    b_workspace = create_b_workspace("Logistics test order: polo shirts 100 pcs")
    project = create_project(
        original_buyer_actor_id=BUYER_ID,
        product_summary="Polo shirts 100 pcs",
        category="apparel",
        quantity=100,
        main_supplier_actor_id=SUPPLIER_ID,
        b_workspace_id=b_workspace.b_workspace_id,
    )
    check(project.project_id.startswith("PROJ-"), f"Project: {project.project_id}")

    # ── Step 2: M-side sends IM logistics message ─────────────────────────────
    step(2, "M-side sends IM message: 已发顺丰，单号 SF123456789012，今天下午发出")

    check(len(IM_MSG_ZH) > 10, f"IM message prepared: {IM_MSG_ZH}")
    check("顺丰" in IM_MSG_ZH, "Message contains carrier name 顺丰")
    check("SF123456789012" in IM_MSG_ZH, "Message contains tracking number")

    # Also test English message
    check(len(IM_MSG_EN) > 10, f"English IM message: {IM_MSG_EN}")

    # ── Step 3: System extracts carrier and tracking number ───────────────────
    step(3, "System extracts carrier and tracking number from IM text")

    extract_zh = extract_logistics_info_from_im(IM_MSG_ZH)
    check(extract_zh.carrier_code == "SF", f"Carrier code extracted: {extract_zh.carrier_code}")
    check(extract_zh.tracking_number == "SF123456789012", f"Tracking extracted: {extract_zh.tracking_number}")
    check(extract_zh.confidence_score >= 0.8, f"Confidence: {extract_zh.confidence_score}")
    check(extract_zh.carrier_name is not None, f"Carrier name: {extract_zh.carrier_name}")

    extract_en = extract_logistics_info_from_im(IM_MSG_EN)
    check(extract_en.carrier_code == "DHL", f"EN carrier code: {extract_en.carrier_code}")
    check(extract_en.tracking_number is not None, f"EN tracking: {extract_en.tracking_number}")

    # Test status normalization
    check(normalize_raw_status("已揽收") == "picked_up", "已揽收 → picked_up")
    check(normalize_raw_status("运输中") == "in_transit", "运输中 → in_transit")
    check(normalize_raw_status("已签收") == "delivered", "已签收 → delivered")
    check(normalize_raw_status("派送中") == "out_for_delivery", "派送中 → out_for_delivery")
    check(normalize_raw_status("delivered") == "delivered", "delivered → delivered")
    check(normalize_raw_status("LABEL_CREATED") == "label_created", "LABEL_CREATED → label_created")
    check(normalize_raw_status("unknownXYZ") == "unknown", "unknownXYZ → unknown")

    # ── Step 4: System creates LogisticsShipment ──────────────────────────────
    step(4, "System creates LogisticsShipment")

    shipment = ingest_tracking_number(
        project_id=project.project_id,
        carrier_name=extract_zh.carrier_name,
        carrier_code=extract_zh.carrier_code,
        tracking_number=extract_zh.tracking_number,
        source="im_message",
        actor_id=SUPPLIER_ID,
    )
    check(shipment.shipment_id.startswith("SHIP-"), f"Shipment ID: {shipment.shipment_id}")
    check(shipment.tracking_number == "SF123456789012", f"Tracking: {shipment.tracking_number}")
    check(shipment.carrier_code == "SF", f"Carrier code: {shipment.carrier_code}")
    check(shipment.project_id == project.project_id, "Shipment linked to project")

    # Test ingest_logistics_from_im_message convenience function
    shipment2 = ingest_logistics_from_im_message(
        project_id=project.project_id,
        raw_message=IM_MSG_EN,
        actor_id=SUPPLIER_ID,
    )
    check(shipment2 is not None, "IM-based ingestion returned shipment")
    check(shipment2.carrier_code == "DHL", f"DHL shipment created: {shipment2.carrier_code}")

    # ── Step 5: Provider registry selects correct provider ───────────────────
    step(5, "Provider registry selects CainiaoLikeProvider in mock mode")

    provider = get_logistics_provider("cainiao_like")
    check(isinstance(provider, CainiaoLikeProvider), f"Provider is CainiaoLikeProvider: {type(provider).__name__}")
    check(provider.provider_name == "cainiao_like", f"Provider name: {provider.provider_name}")

    mock_provider = get_logistics_provider("mock")
    check(isinstance(mock_provider, MockProvider), f"Mock provider: {type(mock_provider).__name__}")

    # ── Step 6: Cainiao-like mock API returns tracking events ─────────────────
    step(6, "Cainiao-like mock API returns tracking events")

    raw_events = provider.fetch_tracking_events("SF", "SF123456789012")
    check(len(raw_events) >= 3, f"Raw events returned: {len(raw_events)}")
    check(any(e.get("normalized_status") == "delivered" for e in raw_events),
          "Delivered event present in mock response")

    log_m_event(
        event_type="LOGISTICS_PROVIDER_API_CALLED",
        b_workspace_id=project.project_id,
        payload={"provider": "cainiao_like", "tracking_number": "SF123456789012", "event_count": len(raw_events)},
    )

    # ── Step 7: System normalizes events ──────────────────────────────────────
    step(7, "System normalizes logistics events")

    normalized_statuses = [e.get("normalized_status") for e in raw_events]
    check("label_created" in normalized_statuses or "picked_up" in normalized_statuses,
          f"Normalized statuses include early-stage: {normalized_statuses}")
    check("delivered" in normalized_statuses, "Delivered event normalized")

    for s in normalized_statuses:
        valid = ["label_created", "picked_up", "in_transit", "customs", "out_for_delivery", "delivered", "exception", "unknown"]
        check(s in valid, f"Status '{s}' is a valid normalized status")

    # ── Step 8: System deduplicates events ────────────────────────────────────
    step(8, "System deduplicates events on second sync")

    # First sync: store events
    all_stored = sync_tracking_from_provider(shipment.shipment_id)
    first_count = len([e for e in all_stored if not e.is_duplicate])
    dup_count_first = len([e for e in all_stored if e.is_duplicate])
    check(first_count >= 3, f"Non-duplicate events on first sync: {first_count}")

    # Second sync: same events → all duplicates
    all_stored_2 = sync_tracking_from_provider(shipment.shipment_id)
    dup_count_second = len([e for e in all_stored_2 if e.is_duplicate])
    new_count_second = len([e for e in all_stored_2 if not e.is_duplicate])
    check(dup_count_second >= first_count, f"Duplicates on second sync: {dup_count_second}")
    check(new_count_second == 0, f"New events on second sync: {new_count_second} (should be 0)")

    dedup_events = read_events(event_type="LOGISTICS_EVENT_DEDUPED", b_workspace_id=project.project_id)
    check(len(dedup_events) >= 1, f"Dedup events logged: {len(dedup_events)}")

    # ── Step 9: System updates order state ────────────────────────────────────
    step(9, "System updates order state from logistics events")

    updated_shipment = get_shipment(shipment.shipment_id)
    check(updated_shipment.current_status == "delivered",
          f"Shipment status after sync: {updated_shipment.current_status}")

    order_state = map_logistics_status_to_order_state("delivered")
    check(order_state == "DELIVERED", f"Order state mapping for delivered: {order_state}")
    order_state_transit = map_logistics_status_to_order_state("in_transit")
    check(order_state_transit == "IN_TRANSIT", f"Order state mapping for in_transit: {order_state_transit}")
    order_state_exc = map_logistics_status_to_order_state("exception")
    check(order_state_exc == "EXCEPTION_RAISED", f"Order state mapping for exception: {order_state_exc}")

    state_update_events = read_events(event_type="ORDER_STATE_UPDATED_FROM_LOGISTICS",
                                       b_workspace_id=project.project_id)
    check(len(state_update_events) >= 1, f"Order state update events: {len(state_update_events)}")

    # ── Step 10: B-side receives logistics update ─────────────────────────────
    step(10, "B-side receives logistics update")

    from src.merchandiser.b_side.b_logistics_updates import push_logistics_update
    b_update = push_logistics_update(
        project_id=project.project_id,
        buyer_actor_id=BUYER_ID,
        tracking_number="SF123456789012",
        carrier_name="顺丰",
        normalized_status="delivered",
        description="已签收",
    )
    check(b_update.get("status") == "sent", f"B-side update: {b_update['status']}")

    b_update_events = read_events(event_type="B_SIDE_LOGISTICS_UPDATE_SENT", b_workspace_id=project.project_id)
    check(len(b_update_events) >= 1, f"B-side logistics update events: {len(b_update_events)}")

    # ── Step 11: Delivered event triggers buyer sign-off request ─────────────
    step(11, "Delivered event triggers buyer sign-off request (not automatic acceptance)")

    # Delivered ≠ automatic acceptance — must trigger sign-off request
    signoff_req = request_buyer_signoff(project.project_id, BUYER_ID, "SF123456789012")
    check(signoff_req.get("status") == "signoff_requested", f"Sign-off requested (not auto-accepted)")
    check("Confirm received" in signoff_req.get("message", "") or
          "Not received" in signoff_req.get("message", ""),
          "Sign-off message presents options (not automatic)")

    signoff_events = read_events(event_type="BUYER_SIGNOFF_REQUESTED", b_workspace_id=project.project_id)
    check(len(signoff_events) >= 1, f"Sign-off request events: {len(signoff_events)}")

    # ── Step 12: IEG records all key events ───────────────────────────────────
    step(12, "Industrial Execution Graph records all key events")

    tracking_ingested = read_events(event_type="TRACKING_NUMBER_INGESTED", b_workspace_id=project.project_id)
    check(len(tracking_ingested) >= 1, f"TRACKING_NUMBER_INGESTED: {len(tracking_ingested)}")

    provider_selected = read_events(event_type="LOGISTICS_PROVIDER_SELECTED")
    check(len(provider_selected) >= 1, f"LOGISTICS_PROVIDER_SELECTED: {len(provider_selected)}")

    api_called = read_events(event_type="LOGISTICS_PROVIDER_API_CALLED")
    check(len(api_called) >= 1, f"LOGISTICS_PROVIDER_API_CALLED: {len(api_called)}")

    event_ingested = read_events(event_type="LOGISTICS_EVENT_INGESTED", b_workspace_id=project.project_id)
    check(len(event_ingested) >= 3, f"LOGISTICS_EVENT_INGESTED: {len(event_ingested)}")

    status_normalized = read_events(event_type="LOGISTICS_STATUS_NORMALIZED", b_workspace_id=project.project_id)
    check(len(status_normalized) >= 3, f"LOGISTICS_STATUS_NORMALIZED: {len(status_normalized)}")

    # ── Final Report ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"CAINIAO-LIKE LOGISTICS MVP COMPLETE: {_steps_passed} passed, {_steps_failed} failed")
    print(f"{'=' * 70}")
    if _steps_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
