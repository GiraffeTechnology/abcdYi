"""Adapter between abcdYi order data and GLTG engine input/output."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from gltg import ApparelOrderInput, DeliveryFeasibilityPacket, LeadTimeGraphEngine
from gltg.models import ParticipantNode

from src.db.models.order import Order
from src.db.models.dynamic_form import DynamicOrderFormVersion
from src.db.models.rfq import RFQ, SupplierResponse, SupplierResponsePacket
from src.db.models.participant import Participant, ParticipantRole, ParticipantProfile
from src.db.models.production import Milestone

_engine = LeadTimeGraphEngine()

# GLTG role names mapped from abcdYi participant role_name values
_ROLE_MAP: dict[str, str] = {
    "MANUFACTURER": "MANUFACTURER",
    "FABRIC_SUPPLIER": "FABRIC_SUPPLIER",
    "TRIM_SUPPLIER": "TRIM_SUPPLIER",
    "PACKAGING_SUPPLIER": "PACKAGING_SUPPLIER",
    "QC_INSPECTOR": "QC_INSPECTOR",
    "LOGISTICS_PROVIDER": "LOGISTICS_PROVIDER",
}


async def _load_response_packet(
    db: AsyncSession, participant_id: uuid.UUID, rfq_id: uuid.UUID
) -> Optional[SupplierResponsePacket]:
    """Load the normalized SupplierResponsePacket for a participant on this RFQ."""
    resp_result = await db.execute(
        select(SupplierResponse).where(
            SupplierResponse.rfq_id == rfq_id,
            SupplierResponse.participant_id == participant_id,
        )
    )
    resp = resp_result.scalar_one_or_none()
    if not resp:
        return None
    pkt_result = await db.execute(
        select(SupplierResponsePacket).where(
            SupplierResponsePacket.supplier_response_id == resp.id
        )
    )
    return pkt_result.scalar_one_or_none()


async def build_gltg_input_from_order(
    db: AsyncSession,
    order: Order,
    rfq_id: Optional[uuid.UUID] = None,
) -> ApparelOrderInput:
    """
    Build a GLTG ApparelOrderInput from an abcdYi Order.

    Pulls participant nodes from:
    - SupplierResponsePackets on the winning RFQ (if rfq_id is provided)
    - ParticipantProfile baseline data for all matched participants

    Falls back to profile-level lead times when packet data is absent.
    """
    # Load form fields for quantity and required delivery date
    form_fields: dict = {}
    required_delivery: Optional[date] = None
    quantity = 0
    product_categories: list[str] = []

    if order.locked_form_version_id:
        version = await db.get(DynamicOrderFormVersion, order.locked_form_version_id)
        if version and version.fields:
            form_fields = version.fields
            quantity = int(form_fields.get("quantity") or 0)
            product_categories = form_fields.get("product_categories") or []
            rd = form_fields.get("required_delivery_date")
            if rd:
                try:
                    if isinstance(rd, str):
                        required_delivery = date.fromisoformat(rd[:10])
                    elif isinstance(rd, date):
                        required_delivery = rd
                except ValueError:
                    pass

    # Load current milestones for reforecasting
    ms_result = await db.execute(
        select(Milestone).where(Milestone.order_id == order.id)
    )
    milestones = list(ms_result.scalars().all())
    milestone_updates: list[dict] = [
        {
            "milestone_type": m.milestone_type,
            "status": m.status,
            "planned_date": m.planned_date.isoformat() if m.planned_date else None,
            "predicted_date": m.predicted_date.isoformat() if m.predicted_date else None,
            "actual_date": m.actual_date.isoformat() if m.actual_date else None,
        }
        for m in milestones
    ]

    # Identify the winning RFQ if not given: find the most recent sent RFQ for this project
    effective_rfq_id = rfq_id
    if effective_rfq_id is None:
        rfq_result = await db.execute(
            select(RFQ)
            .where(RFQ.project_id == order.project_id, RFQ.status == "SENT")
            .order_by(RFQ.created_at.desc())
            .limit(1)
        )
        rfq_row = rfq_result.scalar_one_or_none()
        if rfq_row:
            effective_rfq_id = rfq_row.id

    # Build participant nodes from supplier responses
    participant_nodes: list[ParticipantNode] = []

    if effective_rfq_id:
        # Load all responses for this RFQ
        responses_result = await db.execute(
            select(SupplierResponse).where(SupplierResponse.rfq_id == effective_rfq_id)
        )
        responses = list(responses_result.scalars().all())

        for resp in responses:
            pkt_result = await db.execute(
                select(SupplierResponsePacket).where(
                    SupplierResponsePacket.supplier_response_id == resp.id
                )
            )
            pkt = pkt_result.scalar_one_or_none()

            # Load participant role
            role_result = await db.execute(
                select(ParticipantRole).where(
                    ParticipantRole.participant_id == resp.participant_id,
                    ParticipantRole.is_active == True,
                )
            )
            role_row = role_result.scalars().first()
            role_name = _ROLE_MAP.get(role_row.role_name if role_row else "", "MANUFACTURER")

            # Load profile for baseline data
            profile_result = await db.execute(
                select(ParticipantProfile).where(
                    ParticipantProfile.participant_id == resp.participant_id
                )
            )
            profile = profile_result.scalar_one_or_none()

            node = ParticipantNode(
                participant_id=str(resp.participant_id),
                role=role_name,
                fabric_lead_time_days=pkt.fabric_lead_time_days if pkt else None,
                trim_lead_time_days=pkt.trim_lead_time_days if pkt else None,
                packaging_lead_time_days=pkt.packaging_time_days if pkt else None,
                production_time_days=pkt.production_time_days if pkt else None,
                qc_time_days=pkt.qc_time_days if pkt else None,
                logistics_time_days=pkt.logistics_time_days if pkt else None,
                supplier_stated_lead_time_days=pkt.total_lead_time_days if pkt else None,
                moq=pkt.moq if pkt else (profile.moq if profile else None),
                capacity_available=bool(pkt.capacity_available) if pkt and pkt.capacity_available is not None else None,
                unit_price=pkt.unit_price if pkt else None,
                currency=pkt.currency if pkt else None,
            )
            participant_nodes.append(node)

    return ApparelOrderInput(
        order_id=str(order.id),
        required_delivery_date=required_delivery,
        quantity=quantity,
        product_categories=product_categories if isinstance(product_categories, list) else [],
        participant_nodes=participant_nodes,
        milestone_updates=milestone_updates,
        form_fields=form_fields,
    )


def evaluate_delivery_feasibility(
    gltg_input: ApparelOrderInput,
) -> DeliveryFeasibilityPacket:
    """Run the GLTG engine synchronously and return the result."""
    return _engine.evaluate(gltg_input)
