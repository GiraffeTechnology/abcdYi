import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from src.logistics.schemas import ShipmentCreate, TrackingEventCreate, ShipmentOut
from src.logistics.service import create_shipment, add_tracking_event, get_shipment
from src.db.models.logistics import ShipmentTrackingEvent

router = APIRouter()


@router.post("/orders/{order_id}/shipments", status_code=status.HTTP_201_CREATED, response_model=ShipmentOut)
async def create_shipment_route(
    order_id: uuid.UUID,
    body: ShipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    shipment = await create_shipment(
        db=db,
        order_id=order_id,
        shipment_data=body.model_dump(),
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(shipment)
    return shipment


@router.post("/shipments/{shipment_id}/tracking-events", status_code=status.HTTP_201_CREATED)
async def add_tracking(
    shipment_id: uuid.UUID,
    body: TrackingEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    event = await add_tracking_event(
        db=db,
        shipment_id=shipment_id,
        event_type=body.event_type,
        location=body.location,
        description=body.description,
        occurred_at=body.occurred_at,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(event)
    return {
        "id": str(event.id),
        "shipment_id": str(event.shipment_id),
        "event_type": event.event_type,
        "location": event.location,
        "occurred_at": event.occurred_at.isoformat(),
    }


@router.get("/shipments/{shipment_id}")
async def get_shipment_route(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    shipment = await get_shipment(db, shipment_id, current_user.tenant_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    events_result = await db.execute(
        select(ShipmentTrackingEvent)
        .where(ShipmentTrackingEvent.shipment_id == shipment_id)
        .order_by(ShipmentTrackingEvent.occurred_at)
    )
    events = list(events_result.scalars().all())

    return {
        **ShipmentOut.model_validate(shipment).model_dump(),
        "tracking_events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "location": e.location,
                "description": e.description,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
    }
