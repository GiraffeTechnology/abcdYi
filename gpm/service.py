import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from gpm.config import settings
from gpm.models import ProcessBenchmark, IncomingOrderData, SKUProcessAttribute, VerifiedBusinessData
from gpm.schemas import (
    PriceValidationResult,
    MissingProcessAlert,
    IncomingOrderDataCreate,
    AutoReviewResult,
)


async def query_benchmark(
    db: AsyncSession,
    process_id: str,
    sku_id: str | None = None,
    param_key: str | None = None,
    param_value: str | None = None,
) -> ProcessBenchmark | None:
    conditions = [ProcessBenchmark.process_id == process_id]
    if sku_id is not None:
        conditions.append(ProcessBenchmark.sku_id == sku_id)
    if param_key is not None:
        conditions.append(ProcessBenchmark.param_key == param_key)
    if param_value is not None:
        conditions.append(ProcessBenchmark.param_value == param_value)

    result = await db.execute(
        select(ProcessBenchmark).where(and_(*conditions)).limit(1)
    )
    return result.scalar_one_or_none()


async def list_benchmarks(
    db: AsyncSession,
    process_id: str | None = None,
    sku_id: str | None = None,
) -> list[ProcessBenchmark]:
    conditions = []
    if process_id:
        conditions.append(ProcessBenchmark.process_id == process_id)
    if sku_id:
        conditions.append(ProcessBenchmark.sku_id == sku_id)

    stmt = select(ProcessBenchmark)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await db.execute(stmt)
    return list(result.scalars().all())


def _compute_deviation(unit_price: float, avg_price: float) -> float:
    if avg_price == 0:
        return 0.0
    return abs(unit_price - avg_price) / avg_price


def _classify_deviation(
    deviation_rate: float,
) -> Literal["VALID", "NEEDS_REVIEW", "EXCLUDED"]:
    if deviation_rate <= settings.GPM_DEVIATION_THRESHOLD_VALID:
        return "VALID"
    if deviation_rate <= settings.GPM_DEVIATION_THRESHOLD_REVIEW:
        return "NEEDS_REVIEW"
    return "EXCLUDED"


async def validate_price(
    db: AsyncSession,
    process_id: str,
    unit_price: float,
    sku_id: str | None = None,
    param_key: str | None = None,
    param_value: str | None = None,
) -> PriceValidationResult:
    benchmark = await query_benchmark(db, process_id, sku_id, param_key, param_value)

    if benchmark is None:
        return PriceValidationResult(
            process_id=process_id,
            unit_price=unit_price,
            avg_price=None,
            std_dev=None,
            sample_size=None,
            source_type=None,
            deviation_rate=None,
            classification="NO_BENCHMARK",
            benchmark_found=False,
        )

    deviation_rate = _compute_deviation(unit_price, benchmark.avg_price)
    classification = _classify_deviation(deviation_rate)

    return PriceValidationResult(
        process_id=process_id,
        unit_price=unit_price,
        avg_price=benchmark.avg_price,
        std_dev=benchmark.std_dev,
        sample_size=benchmark.sample_size,
        source_type=benchmark.source_type,
        deviation_rate=deviation_rate,
        classification=classification,
        benchmark_found=True,
    )


async def check_missing_processes(
    db: AsyncSession,
    sku_id: str,
    declared_process_ids: list[str],
) -> MissingProcessAlert:
    result = await db.execute(
        select(SKUProcessAttribute.process_id)
        .where(SKUProcessAttribute.sku_id == sku_id)
        .distinct()
    )
    expected = {row[0] for row in result.all()}
    declared = set(declared_process_ids)
    missing = sorted(expected - declared)

    return MissingProcessAlert(
        sku_id=sku_id,
        missing_process_ids=missing,
        message=(
            f"{len(missing)} process(es) expected for SKU {sku_id} not found in declaration."
            if missing
            else f"All expected processes for SKU {sku_id} are accounted for."
        ),
    )


async def submit_incoming_order(
    db: AsyncSession,
    payload: IncomingOrderDataCreate,
) -> IncomingOrderData:
    if payload.target_layer == "client_proprietary" and not payload.client_id:
        raise ValueError("client_id is required when target_layer is 'client_proprietary'")

    row = IncomingOrderData(
        id=uuid.uuid4(),
        order_id=payload.order_id,
        sku_id=payload.sku_id,
        process_id=payload.process_id,
        param_key=payload.param_key,
        param_value=payload.param_value,
        unit_price=payload.unit_price,
        currency=payload.currency,
        supplier=payload.supplier,
        quote_date=payload.quote_date,
        source=payload.source,
        review_status="PENDING",
        target_layer=payload.target_layer,
        client_id=payload.client_id,
        auto_confirmed=False,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def review_incoming_order(
    db: AsyncSession,
    row_id: uuid.UUID,
    decision: Literal["CONFIRMED", "REJECTED"],
    reviewer_id: str,
    notes: str | None = None,
) -> IncomingOrderData:
    row = await db.get(IncomingOrderData, row_id)
    if row is None:
        raise ValueError(f"IncomingOrderData {row_id} not found")
    if row.review_status != "PENDING":
        raise ValueError(f"Row {row_id} is already in status {row.review_status}")

    row.review_status = decision
    row.reviewed_at = datetime.now(timezone.utc)
    row.reviewed_by = reviewer_id
    row.review_notes = notes

    if decision == "CONFIRMED":
        await _promote_to_verified(db, row)

    await db.flush()
    await db.refresh(row)
    return row


async def _promote_to_verified(db: AsyncSession, row: IncomingOrderData) -> None:
    """Move a confirmed buffer row into verified_business_data."""
    verified = VerifiedBusinessData(
        id=uuid.uuid4(),
        sku_id=row.sku_id,
        process_id=row.process_id,
        param_key=row.param_key,
        param_value=row.param_value,
        unit_price=row.unit_price,
        currency=row.currency,
        supplier=row.supplier,
        quote_date=row.quote_date,
        source=row.source,
        target_layer=row.target_layer,
        client_id=row.client_id,
    )
    db.add(verified)


async def get_universal_training_data(
    db: AsyncSession,
    process_id: str | None = None,
) -> list[VerifiedBusinessData]:
    """
    Returns ONLY records eligible for giraffe_universal_model training.
    Hard filter: target_layer = 'universal' — client_proprietary rows are
    structurally excluded regardless of any other condition.
    This is the only sanctioned entry point for feeding the universal model.
    """
    conditions = [VerifiedBusinessData.target_layer == "universal"]
    if process_id:
        conditions.append(VerifiedBusinessData.process_id == process_id)
    result = await db.execute(
        select(VerifiedBusinessData).where(and_(*conditions))
    )
    return list(result.scalars().all())


async def run_auto_review(db: AsyncSession) -> AutoReviewResult:
    """
    Apply threshold-based rules to PENDING buffer rows.
    Rows within valid deviation are auto-confirmed; rows above exclusion threshold
    are auto-rejected; rows in between remain for human review.
    """
    result = await db.execute(
        select(IncomingOrderData).where(IncomingOrderData.review_status == "PENDING")
    )
    pending = list(result.scalars().all())

    auto_confirmed = 0
    pending_human = 0
    excluded = 0

    for row in pending:
        benchmark = await query_benchmark(db, row.process_id, row.sku_id, row.param_key, row.param_value)

        if benchmark is None:
            pending_human += 1
            continue

        deviation = _compute_deviation(row.unit_price, benchmark.avg_price)
        classification = _classify_deviation(deviation)

        if classification == "VALID":
            row.review_status = "CONFIRMED"
            row.reviewed_at = datetime.now(timezone.utc)
            row.reviewed_by = "system:auto_review"
            row.review_notes = f"Auto-confirmed: deviation {deviation:.2%} within valid threshold {settings.GPM_DEVIATION_THRESHOLD_VALID:.0%}"
            row.auto_confirmed = True
            await _promote_to_verified(db, row)
            auto_confirmed += 1
        elif classification == "EXCLUDED":
            row.review_status = "REJECTED"
            row.reviewed_at = datetime.now(timezone.utc)
            row.reviewed_by = "system:auto_review"
            row.review_notes = f"Auto-rejected: deviation {deviation:.2%} exceeds exclusion threshold {settings.GPM_DEVIATION_THRESHOLD_REVIEW:.0%}"
            excluded += 1
        else:
            pending_human += 1

    await db.flush()
    return AutoReviewResult(
        processed=len(pending),
        auto_confirmed=auto_confirmed,
        pending_human_review=pending_human,
        excluded=excluded,
    )
