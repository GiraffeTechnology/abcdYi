import pytest
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_create_shipment(auth_client, seed_ready_to_ship_order):
    resp = await auth_client.post(
        f"/api/orders/{seed_ready_to_ship_order['id']}/shipments",
        json={
            "carrier": "COSCO",
            "tracking_number": "COSU123456",
            "trade_term": "FOB",
            "origin": "Shenzhen",
            "destination": "Hamburg",
        },
    )
    assert resp.status_code == 201, resp.text

    order_resp = await auth_client.get(f"/api/orders/{seed_ready_to_ship_order['id']}")
    assert order_resp.json()["status"] == "SHIPPED"


@pytest.mark.asyncio
async def test_cannot_ship_non_ready_order(auth_client, seed_confirmed_order):
    resp = await auth_client.post(
        f"/api/orders/{seed_confirmed_order['id']}/shipments",
        json={"carrier": "DHL"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_add_tracking_event(auth_client, seed_shipment):
    resp = await auth_client.post(
        f"/api/shipments/{seed_shipment['id']}/tracking-events",
        json={
            "event_type": "DEPARTED",
            "location": "Shenzhen Port",
            "description": "Container loaded and vessel departed",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["event_type"] == "DEPARTED"


@pytest.mark.asyncio
async def test_delivery_event_transitions_order(auth_client, seed_shipment, seed_ready_to_ship_order):
    await auth_client.post(
        f"/api/shipments/{seed_shipment['id']}/tracking-events",
        json={
            "event_type": "DELIVERED",
            "location": "Hamburg",
            "description": "Delivered",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    order_resp = await auth_client.get(f"/api/orders/{seed_ready_to_ship_order['id']}")
    assert order_resp.json()["status"] == "DELIVERED"


@pytest.mark.asyncio
async def test_get_shipment_with_events(auth_client, seed_shipment):
    await auth_client.post(
        f"/api/shipments/{seed_shipment['id']}/tracking-events",
        json={
            "event_type": "IN_TRANSIT",
            "location": "Singapore",
            "description": "In transit",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    resp = await auth_client.get(f"/api/shipments/{seed_shipment['id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert "tracking_events" in data
    assert len(data["tracking_events"]) >= 1


@pytest.mark.asyncio
async def test_buyer_signoff_updates_supplier_memory(auth_client, seed_delivered_order, db):
    await auth_client.post(f"/api/orders/{seed_delivered_order['id']}/buyer-sign-off")

    from sqlalchemy import select
    from src.db.models.logistics import SupplierMemoryRecord
    import uuid
    result = await db.execute(
        select(SupplierMemoryRecord).where(
            SupplierMemoryRecord.order_id == uuid.UUID(seed_delivered_order["id"])
        )
    )
    records = result.scalars().all()
    assert len(records) >= 1
