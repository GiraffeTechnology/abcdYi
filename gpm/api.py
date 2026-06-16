import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from gpm.auth import require_gpm_api_key
from gpm.db import get_gpm_db
from gpm.schemas import (
    ProcessBenchmarkOut,
    PriceValidationRequest,
    PriceValidationResult,
    MissingProcessCheckRequest,
    MissingProcessAlert,
    IncomingOrderDataCreate,
    IncomingOrderDataOut,
    ReviewDecision,
    AutoReviewResult,
)
from gpm.service import (
    list_benchmarks,
    validate_price,
    check_missing_processes,
    submit_incoming_order,
    review_incoming_order,
    run_auto_review,
)
from gpm.models import IncomingOrderData
from sqlalchemy import select, and_

router = APIRouter(dependencies=[Depends(require_gpm_api_key)])


# ── Read endpoints (abcdyi calls these) ──────────────────────────────────────

@router.get("/benchmarks", response_model=list[ProcessBenchmarkOut], tags=["benchmarks"])
async def get_benchmarks(
    process_id: str | None = Query(None),
    sku_id: str | None = Query(None),
    db: AsyncSession = Depends(get_gpm_db),
):
    return await list_benchmarks(db, process_id=process_id, sku_id=sku_id)


@router.post("/benchmarks/validate", response_model=PriceValidationResult, tags=["benchmarks"])
async def validate_price_route(
    body: PriceValidationRequest,
    db: AsyncSession = Depends(get_gpm_db),
):
    return await validate_price(
        db,
        process_id=body.process_id,
        unit_price=body.unit_price,
        sku_id=body.sku_id,
        param_key=body.param_key,
        param_value=body.param_value,
    )


@router.post("/processes/missing-check", response_model=MissingProcessAlert, tags=["processes"])
async def missing_process_check(
    body: MissingProcessCheckRequest,
    db: AsyncSession = Depends(get_gpm_db),
):
    return await check_missing_processes(db, body.sku_id, body.declared_process_ids)


# ── Write endpoint (abcdyi submits order data to buffer) ─────────────────────

@router.post("/incoming-orders", response_model=IncomingOrderDataOut, status_code=201, tags=["incoming-orders"])
async def create_incoming_order(
    body: IncomingOrderDataCreate,
    db: AsyncSession = Depends(get_gpm_db),
):
    try:
        row = await submit_incoming_order(db, body)
        await db.commit()
        return row
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


# ── Review endpoints (internal GPM operators only) ───────────────────────────

@router.get("/incoming-orders", response_model=list[IncomingOrderDataOut], tags=["incoming-orders"])
async def list_incoming_orders(
    review_status: str | None = Query(None, description="Filter by status: PENDING | CONFIRMED | REJECTED"),
    target_layer: str | None = Query(None),
    client_id: str | None = Query(None),
    db: AsyncSession = Depends(get_gpm_db),
):
    conditions = []
    if review_status:
        conditions.append(IncomingOrderData.review_status == review_status)
    if target_layer:
        conditions.append(IncomingOrderData.target_layer == target_layer)
    if client_id:
        conditions.append(IncomingOrderData.client_id == client_id)

    stmt = select(IncomingOrderData)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(IncomingOrderData.written_at.desc())

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/incoming-orders/{row_id}/review", response_model=IncomingOrderDataOut, tags=["incoming-orders"])
async def review_order(
    row_id: uuid.UUID,
    body: ReviewDecision,
    db: AsyncSession = Depends(get_gpm_db),
):
    try:
        row = await review_incoming_order(
            db, row_id, body.decision, body.reviewer_id, body.notes
        )
        await db.commit()
        return row
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/incoming-orders/auto-review", response_model=AutoReviewResult, tags=["incoming-orders"])
async def trigger_auto_review(
    db: AsyncSession = Depends(get_gpm_db),
):
    result = await run_auto_review(db)
    await db.commit()
    return result
