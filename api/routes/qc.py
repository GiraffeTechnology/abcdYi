import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db, get_current_user
from src.qc.schemas import QCStandardOut, QCRecordCreate, QCRecordOut
from src.qc.service import (
    create_qc_standard, record_qc_result,
    mark_qc_pass, mark_qc_fail, get_qc_records_for_order,
)

router = APIRouter()


class QCStandardCreateBody(BaseModel):
    form_version_id: uuid.UUID


class MarkFailBody(BaseModel):
    responsible_participant_id: uuid.UUID


@router.post("/orders/{order_id}/qc-standards", status_code=status.HTTP_201_CREATED, response_model=QCStandardOut)
async def create_qc_standard_route(
    order_id: uuid.UUID,
    body: QCStandardCreateBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    std = await create_qc_standard(
        db=db,
        order_id=order_id,
        form_version_id=body.form_version_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(std)
    return std


@router.post("/orders/{order_id}/qc-records", status_code=status.HTTP_201_CREATED)
async def record_qc(
    order_id: uuid.UUID,
    body: QCRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = await record_qc_result(
        db=db,
        order_id=order_id,
        qc_data=body.model_dump(),
        inspector_participant_id=body.inspector_participant_id,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
    )
    await db.commit()
    await db.refresh(record)
    return QCRecordOut.model_validate(record)


@router.get("/orders/{order_id}/qc-records", response_model=list[QCRecordOut])
async def list_qc_records(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return await get_qc_records_for_order(db, order_id)


@router.post("/qc-records/{qc_record_id}/mark-pass", response_model=QCRecordOut)
async def mark_pass(
    qc_record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = await mark_qc_pass(db, qc_record_id, current_user.id)
    await db.commit()
    await db.refresh(record)
    return record


@router.post("/qc-records/{qc_record_id}/mark-fail", response_model=QCRecordOut)
async def mark_fail(
    qc_record_id: uuid.UUID,
    body: MarkFailBody,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    record = await mark_qc_fail(db, qc_record_id, body.responsible_participant_id, current_user.id)
    await db.commit()
    await db.refresh(record)
    return record
