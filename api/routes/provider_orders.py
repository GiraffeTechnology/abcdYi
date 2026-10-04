"""Authenticated same-provider handoff from Aivan confirmation to abcdYi."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from api.deps import get_current_user, get_db
from src.integrations.confirmed_orders import ConfirmedOrderError, ConfirmedOrderProvider
from src.order_confirmation.provider_handoff import import_confirmed_order
from src.orders.schemas import OrderOut

router = APIRouter()


class ConfirmedProviderOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    purchase_order_id: str = Field(min_length=1, max_length=255)


def get_confirmed_order_provider(current_user=Depends(get_current_user)) -> ConfirmedOrderProvider:
    try:
        return ConfirmedOrderProvider(local_tenant_id=str(current_user.tenant_id))
    except ConfirmedOrderError as exc:
        raise HTTPException(status_code=503, detail={"error": exc.code}) from exc


@router.post("/orders/from-provider-confirmed", response_model=OrderOut)
async def import_order_route(body: ConfirmedProviderOrderRequest, db: AsyncSession = Depends(get_db),
                             current_user=Depends(get_current_user),
                             provider=Depends(get_confirmed_order_provider)):
    try:
        order = await import_confirmed_order(db, tenant_id=current_user.tenant_id, user_id=current_user.id,
                                            po_id=body.purchase_order_id, provider=provider)
        await db.commit()
        await db.refresh(order)
        return order
    except ConfirmedOrderError as exc:
        await db.rollback()
        raise HTTPException(status_code=exc.status_code, detail={"error": exc.code}) from exc
    except IntegrityError as exc:
        await db.rollback()
        # The deterministic source identity makes retry safe after another
        # importer commits. Never replace an existing execution order.
        raise HTTPException(status_code=409, detail={"error": "IMPORT_CONFLICT_RETRY_SAME_PO"}) from exc
