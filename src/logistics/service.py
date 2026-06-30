import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.logistics import Shipment, ShipmentTrackingEvent
from src.db.models.order import Order
from src.orders.state_machine import transition
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import LOGISTICS_HANDOVER_CREATED, SHIPMENT_UPDATED

DELIVERY_EVENT_TYPES = {"DELIVERED", "ARRIVAL", "POD", "PROOF_OF_DELIVERY"}


async def create_shipment(
    db: AsyncSession,
    order_id: uuid.UUID,
    shipment_data: dict,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Shipment:
    order = await db.get(Order, order_id)
    if not order:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != "READY_TO_SHIP":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=409,
            detail=f"Cannot create shipment for order in status {order.status}. Must be READY_TO_SHIP.",
        )

    shipment = Shipment(
        order_id=order_id,
        logistics_provider_participant_id=shipment_data.get("logistics_provider_participant_id"),
        carrier=shipment_data.get("carrier"),
        tracking_number=shipment_data.get("tracking_number"),
        trade_term=shipment_data.get("trade_term"),
        origin=shipment_data.get("origin"),
        destination=shipment_data.get("destination"),
        estimated_departure_date=shipment_data.get("estimated_departure_date"),
        estimated_arrival_date=shipment_data.get("estimated_arrival_date"),
    )
    db.add(shipment)

    order.status = transition(order.status, "SHIPPED")
    await db.flush()

    await emit_event(
        db=db,
        event_type=LOGISTICS_HANDOVER_CREATED,
        payload={"shipment_id": str(shipment.id), "order_id": str(order_id)},
        tenant_id=tenant_id,
        order_id=order_id,
        triggered_by_user_id=user_id,
    )
    return shipment


async def add_tracking_event(
    db: AsyncSession,
    shipment_id: uuid.UUID,
    event_type: str,
    location: str | None,
    description: str | None,
    occurred_at: datetime,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> ShipmentTrackingEvent:
    shipment = await db.get(Shipment, shipment_id)
    if not shipment:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Shipment not found")

    tracking_event = ShipmentTrackingEvent(
        shipment_id=shipment_id,
        event_type=event_type,
        location=location,
        description=description,
        occurred_at=occurred_at,
    )
    db.add(tracking_event)

    # Check if delivery event → update order to DELIVERED
    if event_type.upper() in DELIVERY_EVENT_TYPES:
        order = await db.get(Order, shipment.order_id)
        if order and order.status == "SHIPPED":
            order.status = transition(order.status, "DELIVERED")
            shipment.actual_arrival_date = occurred_at

    await db.flush()

    await emit_event(
        db=db,
        event_type=SHIPMENT_UPDATED,
        payload={
            "shipment_id": str(shipment_id),
            "event_type": event_type,
            "order_id": str(shipment.order_id),
        },
        tenant_id=tenant_id,
        order_id=shipment.order_id,
        triggered_by_user_id=user_id,
    )
    return tracking_event


async def get_shipment(
    db: AsyncSession, shipment_id: uuid.UUID, tenant_id: uuid.UUID
) -> Shipment | None:
    from src.db.tenant_scope import get_order_owned
    return await get_order_owned(db, Shipment, shipment_id, tenant_id)
