from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException
from src.execution_access import require_order
from src.order_confirmation.approval_binding import validate_quote_binding, require_commercial_actor
from src.db.models.order import Order, OrderLine
from src.db.models.decision import DecisionPacket, DecisionOption
from src.db.tenant_scope import get_project_owned
from src.db.models.dynamic_form import DynamicOrderForm, DynamicOrderFormVersion
from src.db.models.production import Milestone
from src.orders.state_machine import transition
from src.milestones.constants import ORDERED_MILESTONES
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import ORDER_CREATED, ORDER_CONFIRMED, BUYER_SIGNED_OFF


def _generate_order_number(seq: int) -> str:
    year = datetime.now(timezone.utc).year
    return f"ORD-{year}-{seq:04d}"


async def _next_order_seq(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(Order))
    return (result.scalar() or 0) + 1


def _planned_date(base: datetime, days: int | None) -> datetime | None:
    if days is None:
        return None
    return base + timedelta(days=days)


async def create_order_from_approved_option(
    db: AsyncSession,
    project_id: uuid.UUID,
    packet_id: uuid.UUID,
    option_id: uuid.UUID,
    approval_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Order:
    packet, option, form, version, approval_binding = await validate_quote_binding(
        db, project_id=project_id, packet_id=packet_id, option_id=option_id,
        approval_id=approval_id, tenant_id=tenant_id)
    form_version_id, form_fields = version.id, version.fields or {}
    # The locked packet serializes duplicate submissions of this approved quote.
    existing = await db.scalar(select(Order).where(Order.project_id == project_id,
        Order.approved_option_id == option_id, Order.locked_form_version_id == version.id))
    if existing is not None:
        return existing

    order = Order(
        project_id=project_id,
        approved_option_id=option_id,
        locked_form_version_id=form_version_id,
        status="DRAFT_FROM_APPROVED_QUOTE",
        order_number=f"ORD-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:12].upper()}",
    )
    db.add(order)
    await db.flush()

    # Create order line from form fields
    product_type = form_fields.get("product_type", "Apparel")
    quantity = form_fields.get("quantity") or 1
    line = OrderLine(
        order_id=order.id,
        line_number=1,
        description=str(product_type),
        quantity=int(quantity),
        unit="pcs",
        unit_price=option.unit_price,
        currency=option.currency,
        attributes={"form_fields_snapshot": form_fields},
    )
    db.add(line)

    # Lock the dynamic form
    if form:
        form.is_locked = True

    # Create 12 milestones
    base = datetime.now(timezone.utc)
    lt = option.lead_time_breakdown or {}
    seq_days = lt.get("sequential_days", {})
    par_days = lt.get("parallel_breakdown", {})

    fabric_lt = par_days.get("fabric_lead_time_days")
    production_lt = seq_days.get("production_time_days")
    qc_lt = seq_days.get("qc_time_days")
    logistics_lt = seq_days.get("logistics_time_days")

    milestone_dates = {
        "SAMPLE_CONFIRMATION": _planned_date(base, 7),
        "FABRIC_BOOKING": _planned_date(base, fabric_lt),
        "TRIM_BOOKING": _planned_date(base, par_days.get("trim_lead_time_days")),
        "CUTTING": _planned_date(base, (fabric_lt or 0) + 3) if fabric_lt else None,
        "SEWING": None,
        "WASHING_OR_FINISHING": None,
        "INLINE_QC": None,
        "FINAL_QC": None,
        "PACKING": None,
        "LOGISTICS_HANDOVER": None,
        "SHIPMENT": None,
        "BUYER_SIGN_OFF": None,
    }

    # Sequential after CUTTING
    cutting_days = (fabric_lt or 0) + 3 if fabric_lt else None
    if cutting_days is not None and production_lt is not None:
        sewing_days = cutting_days + production_lt
        milestone_dates["SEWING"] = _planned_date(base, sewing_days)
        milestone_dates["WASHING_OR_FINISHING"] = _planned_date(base, sewing_days + 2)
        milestone_dates["INLINE_QC"] = _planned_date(base, sewing_days + 3)
        if qc_lt is not None:
            final_qc_days = sewing_days + qc_lt
            milestone_dates["FINAL_QC"] = _planned_date(base, final_qc_days)
            milestone_dates["PACKING"] = _planned_date(base, final_qc_days + 2)
            milestone_dates["LOGISTICS_HANDOVER"] = _planned_date(base, final_qc_days + 3)
            if logistics_lt is not None:
                shipment_days = final_qc_days + logistics_lt
                milestone_dates["SHIPMENT"] = _planned_date(base, shipment_days)
                milestone_dates["BUYER_SIGN_OFF"] = _planned_date(base, shipment_days + 7)

    for mtype in ORDERED_MILESTONES:
        planned = milestone_dates.get(mtype)
        notes = None if planned else "Planned date not set — lead time missing"
        ms = Milestone(
            order_id=order.id,
            milestone_type=mtype,
            planned_date=planned,
            status="PENDING",
            notes=notes,
        )
        db.add(ms)

    await db.flush()

    await emit_event(
        db=db,
        event_type=ORDER_CREATED,
        payload={
            "order_id": str(order.id),
            "order_number": order.order_number,
            "project_id": str(project_id),
            "approval": approval_binding,
            "locked_form_version_id": str(form_version_id),
        },
        tenant_id=tenant_id,
        project_id=project_id,
        order_id=order.id,
        triggered_by_user_id=user_id,
    )

    return order


async def confirm_order(
    db: AsyncSession,
    order_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Order:
    order = await require_order(db, order_id, tenant_id, lock=True)
    actor_role = await require_commercial_actor(db, user_id, tenant_id)
    if order.confirmed_at is not None:
        return order
    if order.status != "DRAFT_FROM_APPROVED_QUOTE":
        raise HTTPException(status_code=409, detail="Only an approved quotation draft can be confirmed")
    option = await db.get(DecisionOption, order.approved_option_id)
    binding = (option.evidence or {}).get("commercial_approval", {}) if option else {}
    try:
        approval_id = uuid.UUID(binding["approval_id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=403, detail="Order quotation approval evidence is missing") from exc
    await validate_quote_binding(db, project_id=order.project_id, packet_id=option.packet_id,
        option_id=option.id, approval_id=approval_id, tenant_id=tenant_id)
    order.status = transition(order.status, "PENDING_BUYER_CONFIRMATION")
    order.status = transition(order.status, "CONFIRMED")
    order.confirmed_at = datetime.now(timezone.utc)
    await db.flush()

    await emit_event(
        db=db,
        event_type=ORDER_CONFIRMED,
        payload={"order_id": str(order_id), "order_number": order.order_number,
            "actor_id": str(user_id), "actor_role": actor_role, "confirmed_at": order.confirmed_at.isoformat(),
            "approval": binding},
        tenant_id=tenant_id,
        project_id=order.project_id,
        order_id=order_id,
        triggered_by_user_id=user_id,
    )

    order.status = transition(order.status, "IN_PRODUCTION")
    await db.flush()

    return order


async def buyer_sign_off(
    db: AsyncSession,
    order_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Order:
    order = await require_order(db, order_id, tenant_id, lock=True)
    actor_role = await require_commercial_actor(db, user_id, tenant_id, buyer_only=True)
    if order.status == "BUYER_SIGNED_OFF":
        return order

    if order.status != "DELIVERED":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot sign off order in status {order.status}. Must be DELIVERED.",
        )

    order.status = transition(order.status, "BUYER_SIGNED_OFF")
    order.buyer_signed_off_at = datetime.now(timezone.utc)
    await db.flush()

    await emit_event(
        db=db,
        event_type=BUYER_SIGNED_OFF,
        payload={"order_id": str(order_id), "actor_id": str(user_id), "actor_role": actor_role,
            "signed_off_at": order.buyer_signed_off_at.isoformat()},
        tenant_id=tenant_id,
        project_id=order.project_id,
        order_id=order_id,
        triggered_by_user_id=user_id,
    )

    # Update supplier memory records after sign-off
    from src.supplier_memory.service import update_supplier_memory_after_signoff
    await update_supplier_memory_after_signoff(db, order_id, tenant_id, user_id=user_id)

    return order
