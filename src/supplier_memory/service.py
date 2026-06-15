import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models.logistics import SupplierMemoryRecord, Shipment
from src.db.models.production import Milestone
from src.db.models.qc import QCRecord
from src.db.models.rfq import RFQRecipient
from src.db.models.decision import DecisionOption
from src.db.models.order import Order
from src.milestones.constants import SHIPMENT as SHIPMENT_MILESTONE


async def update_supplier_memory_after_signoff(
    db: AsyncSession,
    order_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> list[SupplierMemoryRecord]:
    """
    Called after buyer_sign_off. Creates SupplierMemoryRecord for participants.
    """
    order = await db.get(Order, order_id)
    if not order:
        return []

    # Get participant IDs from the approved option
    participant_ids: set[uuid.UUID] = set()
    if order.approved_option_id:
        option = await db.get(DecisionOption, order.approved_option_id)
        if option and option.supplier_combination:
            for pid_str in option.supplier_combination.values():
                try:
                    participant_ids.add(uuid.UUID(str(pid_str)))
                except (ValueError, TypeError):
                    pass

    records_created: list[SupplierMemoryRecord] = []

    for participant_id in participant_ids:
        # On-time delivery: SHIPMENT milestone actual_date <= planned_date
        ms_result = await db.execute(
            select(Milestone).where(
                Milestone.order_id == order_id,
                Milestone.milestone_type == SHIPMENT_MILESTONE,
            )
        )
        shipment_milestone = ms_result.scalar_one_or_none()
        on_time = None
        if shipment_milestone and shipment_milestone.actual_date and shipment_milestone.planned_date:
            on_time = shipment_milestone.actual_date <= shipment_milestone.planned_date

        # QC pass rate for this participant
        qc_result = await db.execute(
            select(QCRecord).where(
                QCRecord.order_id == order_id,
                QCRecord.responsible_participant_id == participant_id,
            )
        )
        qc_records = list(qc_result.scalars().all())
        if qc_records:
            passed = sum(1 for r in qc_records if r.result == "QC_PASSED")
            qc_pass_rate = passed / len(qc_records)
        else:
            qc_pass_rate = None

        # Response time from RFQRecipient
        recip_result = await db.execute(
            select(RFQRecipient).where(
                RFQRecipient.participant_id == participant_id,
            ).order_by(RFQRecipient.responded_at.desc()).limit(1)
        )
        recipient = recip_result.scalar_one_or_none()
        response_time_hours = None
        if recipient and recipient.sent_at and recipient.responded_at:
            delta = recipient.responded_at - recipient.sent_at
            response_time_hours = delta.total_seconds() / 3600

        notes = (
            f"Auto-generated from order {order_id}. "
            f"On-time: {on_time}. QC pass rate: {qc_pass_rate}."
        )

        memory = SupplierMemoryRecord(
            participant_id=participant_id,
            order_id=order_id,
            on_time_delivery=on_time,
            qc_pass_rate=qc_pass_rate,
            response_time_hours=response_time_hours,
            notes=notes,
        )
        db.add(memory)
        records_created.append(memory)

    await db.flush()
    return records_created


async def get_supplier_memory_summary(
    db: AsyncSession, participant_id: uuid.UUID
) -> dict:
    result = await db.execute(
        select(SupplierMemoryRecord).where(
            SupplierMemoryRecord.participant_id == participant_id
        ).order_by(SupplierMemoryRecord.recorded_at.desc())
    )
    records = list(result.scalars().all())

    if not records:
        return {
            "participant_id": str(participant_id),
            "order_count": 0,
            "avg_qc_pass_rate": None,
            "on_time_rate": None,
            "avg_response_time_hours": None,
            "last_updated": None,
        }

    qc_rates = [r.qc_pass_rate for r in records if r.qc_pass_rate is not None]
    otd_values = [1.0 if r.on_time_delivery else 0.0
                  for r in records if r.on_time_delivery is not None]
    rt_values = [r.response_time_hours for r in records if r.response_time_hours is not None]

    return {
        "participant_id": str(participant_id),
        "order_count": len(records),
        "avg_qc_pass_rate": sum(qc_rates) / len(qc_rates) if qc_rates else None,
        "on_time_rate": sum(otd_values) / len(otd_values) if otd_values else None,
        "avg_response_time_hours": sum(rt_values) / len(rt_values) if rt_values else None,
        "last_updated": records[0].recorded_at.isoformat() if records else None,
    }
