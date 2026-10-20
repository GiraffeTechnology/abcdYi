from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException
from src.execution_access import require_order, require_order_child, require_participant, require_resolution_actor
from src.db.models.qc import QCStandard, QCRecord
from src.db.models.order import Order
from src.orders.state_machine import transition
from src.apparel_inspection.service import evaluate_qc_record
from src.quality_standards.service import create_qc_standard_from_form
from src.quality_ledger.service import create_quality_incident
from src.execution_graph.writer import emit_event
from src.execution_graph.event_types import QC_RECORD_RECEIVED, QC_PASSED, QC_FAILED


async def create_qc_standard(
    db: AsyncSession,
    order_id: uuid.UUID,
    form_version_id: uuid.UUID,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> QCStandard:
    order = await require_order(db, order_id, tenant_id)
    if order.locked_form_version_id != form_version_id:
        raise HTTPException(status_code=409, detail="QC criteria must use the confirmed order requirement version")
    existing = await db.scalar(select(QCStandard).where(QCStandard.order_id == order_id))
    if existing is not None:
        return existing
    return await create_qc_standard_from_form(db, order_id, form_version_id, tenant_id, user_id)


async def record_qc_result(
    db: AsyncSession,
    order_id: uuid.UUID,
    qc_data: dict,
    inspector_participant_id: uuid.UUID | None,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> QCRecord:
    order = await require_order(db, order_id, tenant_id, lock=True)
    if order.status != "QC_PENDING":
        raise HTTPException(status_code=409, detail="QC inspection requires QC_PENDING; resolve failures before reinspection")
    await require_participant(db, inspector_participant_id, tenant_id)
    await require_participant(db, qc_data.get("responsible_participant_id"), tenant_id)
    if not any(qc_data.get(key) is not None and qc_data.get(key) != {} for key in (
        "fabric_defects", "size_deviation", "color_difference", "label_compliance", "packaging_compliance"
    )):
        raise HTTPException(status_code=422, detail="QC inspection requires recorded inspection criteria and results")

    # Load QC standard for this order
    std_result = await db.execute(
        select(QCStandard).where(QCStandard.order_id == order_id)
    )
    qc_standard = std_result.scalar_one_or_none()
    std_dict = {}
    if qc_standard:
        std_dict = {
            "fabric_defect_limits": qc_standard.fabric_defect_limits or {},
            "size_deviation_limits": qc_standard.size_deviation_limits or {},
            "color_difference_tolerance": qc_standard.color_difference_tolerance or {},
        }

    # Evaluate QC
    try:
        evaluation = evaluate_qc_record(qc_data, std_dict)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail="QC numeric observations require valid recorded criteria") from exc

    responsible_participant_id = qc_data.get("responsible_participant_id")

    record = QCRecord(
        order_id=order_id,
        qc_standard_id=qc_standard.id if qc_standard else None,
        inspector_participant_id=inspector_participant_id,
        measurement_results=qc_data.get("measurement_results"),
        fabric_defects=qc_data.get("fabric_defects"),
        stitching_defects=qc_data.get("stitching_defects"),
        color_difference=qc_data.get("color_difference"),
        size_deviation=qc_data.get("size_deviation"),
        washing_result=qc_data.get("washing_result"),
        label_compliance=qc_data.get("label_compliance"),
        packaging_compliance=qc_data.get("packaging_compliance"),
        photo_evidence_metadata=qc_data.get("photo_evidence_metadata"),
        inspection_report_metadata=qc_data.get("inspection_report_metadata"),
        result=evaluation["result"],
        rework_required=evaluation["rework_required"],
        responsible_participant_id=responsible_participant_id,
        inspected_at=datetime.now(timezone.utc),
    )
    db.add(record)
    await db.flush()

    await emit_event(
        db=db,
        event_type=QC_RECORD_RECEIVED,
        payload={"qc_record_id": str(record.id), "order_id": str(order_id)},
        tenant_id=tenant_id,
        project_id=order.project_id,
        order_id=order_id,
        triggered_by_user_id=user_id,
    )

    if evaluation["result"] == "QC_PASSED":
        if order.status == "QC_PENDING":
            order.status = transition(order.status, "QC_PASSED")
            order.status = transition(order.status, "READY_TO_SHIP")
        await emit_event(
            db=db,
            event_type=QC_PASSED,
            payload={"qc_record_id": str(record.id), "order_id": str(order_id)},
            tenant_id=tenant_id,
            project_id=order.project_id,
            order_id=order_id,
            triggered_by_user_id=user_id,
        )
    else:
        if order.status == "QC_PENDING":
            order.status = transition(order.status, "QC_FAILED")
        await emit_event(
            db=db,
            event_type=QC_FAILED,
            payload={
                "qc_record_id": str(record.id),
                "order_id": str(order_id),
                "failure_reasons": evaluation["failure_reasons"],
            },
            tenant_id=tenant_id,
            project_id=order.project_id,
            order_id=order_id,
            triggered_by_user_id=user_id,
        )
        # Create quality incident if participant identified
        if responsible_participant_id:
            await create_quality_incident(
                db=db,
                order_id=order_id,
                qc_record_id=record.id,
                responsible_participant_id=responsible_participant_id,
                incident_type="QC_FAILURE",
                description=f"QC failed: {'; '.join(evaluation['failure_reasons'])}",
                tenant_id=tenant_id,
            )

    await db.flush()
    return record


async def mark_qc_pass(db: AsyncSession, qc_record_id: uuid.UUID, user_id: uuid.UUID, tenant_id: uuid.UUID) -> QCRecord:
    record = await require_order_child(db, QCRecord, qc_record_id, tenant_id)
    if record.result != "QC_PASSED":
        raise HTTPException(status_code=409, detail="Recorded inspections are immutable; resolve the failure and reinspect")
    return record


async def mark_qc_fail(db: AsyncSession, qc_record_id: uuid.UUID,
                       responsible_participant_id: uuid.UUID, user_id: uuid.UUID, tenant_id: uuid.UUID) -> QCRecord:
    record = await require_order_child(db, QCRecord, qc_record_id, tenant_id)
    await require_participant(db, responsible_participant_id, tenant_id)
    if record.result != "QC_FAILED" or record.responsible_participant_id != responsible_participant_id:
        raise HTTPException(status_code=409, detail="Recorded inspections are immutable; record a new authorized inspection")
    return record


async def resolve_failed_qc(db: AsyncSession, qc_record_id: uuid.UUID, *, tenant_id: uuid.UUID,
                            user_id: uuid.UUID, reason: str) -> QCRecord:
    """Authorize rework without changing the original failed inspection evidence."""
    record = await require_order_child(db, QCRecord, qc_record_id, tenant_id)
    order = await require_order(db, record.order_id, tenant_id, lock=True)
    role = await require_resolution_actor(db, user_id, tenant_id)
    if record.result != "QC_FAILED" or order.status != "QC_FAILED":
        raise HTTPException(status_code=409, detail="Only an unresolved failed QC inspection can enter rework")
    # Resolve only the latest inspection; a prior failure cannot authorize a new cycle.
    latest = await db.scalar(select(QCRecord.id).where(QCRecord.order_id == order.id)
                            .order_by(QCRecord.inspected_at.desc(), QCRecord.created_at.desc()).limit(1))
    if latest != record.id:
        raise HTTPException(status_code=409, detail="Resolve the latest failed inspection")
    if not reason.strip():
        raise HTTPException(status_code=422, detail="A human resolution reason is required")
    order.status = transition(order.status, "IN_PRODUCTION")
    await emit_event(db, "QC_FAILURE_RESOLVED", {
        "qc_record_id": str(record.id), "resolution": "REWORK", "reason": reason.strip(),
        "previous_result": record.result, "previous_status": "QC_FAILED", "status": order.status,
        "actor_id": str(user_id), "actor_role": role,
    }, tenant_id=tenant_id, project_id=order.project_id, order_id=order.id, triggered_by_user_id=user_id)
    await db.flush()
    return record


async def get_qc_records_for_order(db: AsyncSession, order_id: uuid.UUID, tenant_id: uuid.UUID) -> list[QCRecord]:
    await require_order(db, order_id, tenant_id)
    result = await db.execute(select(QCRecord).where(QCRecord.order_id == order_id)
                              .order_by(QCRecord.inspected_at, QCRecord.created_at, QCRecord.id))
    return list(result.scalars().all())
