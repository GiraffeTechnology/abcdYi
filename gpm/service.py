import math
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import select, and_, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from gpm.config import settings, GPMSettings
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


async def submit_test_batch(
    db: AsyncSession,
    records: list[dict],
    batch_id: str,
    cfg: GPMSettings | None = None,
) -> int:
    """
    Insert a batch of test records directly into IncomingOrderData and
    immediately promote them to VerifiedBusinessData.

    This bypasses human review — only allowed when SKIP_HUMAN_REVIEW=True
    and APP_ENV != 'production'.

    Args:
        db: async DB session
        records: list of dicts with keys matching IncomingOrderData fields
                 (process_id, param_key, param_value, unit_price, currency, source, ...)
        batch_id: identifier for this test batch
        cfg: GPMSettings instance (defaults to the module-level settings singleton)

    Returns:
        Number of records inserted.
    """
    effective_cfg = cfg if cfg is not None else settings

    if not effective_cfg.SKIP_HUMAN_REVIEW:
        raise ValueError(
            "submit_test_batch requires SKIP_HUMAN_REVIEW=True. "
            "Set SKIP_HUMAN_REVIEW=true in the environment before running test batch ingestion."
        )

    if effective_cfg.APP_ENV == "production":
        raise ValueError(
            "submit_test_batch is not allowed in production (APP_ENV=production). "
            "Use a test or staging environment."
        )

    now = datetime.now(timezone.utc)
    count = 0

    for rec in records:
        incoming = IncomingOrderData(
            id=uuid.uuid4(),
            order_id=rec.get("order_id", f"test-{batch_id}-{count}"),
            sku_id=rec.get("sku_id"),
            process_id=rec["process_id"],
            param_key=rec.get("param_key"),
            param_value=rec.get("param_value"),
            unit_price=float(rec["unit_price"]),
            currency=rec.get("currency", "CNY"),
            supplier=rec.get("supplier"),
            quote_date=rec.get("quote_date"),
            source=rec.get("source"),
            review_status="test_auto_approved",
            target_layer=rec.get("target_layer", "universal"),
            client_id=rec.get("client_id"),
            written_at=now,
            reviewed_at=now,
            reviewed_by="system:test_batch",
            review_notes=f"Auto-approved as part of test batch {batch_id}",
            auto_confirmed=True,
            batch_id=batch_id,
            is_test_batch=True,
        )
        db.add(incoming)

        # Immediately promote to verified_business_data with batch marker
        verified = VerifiedBusinessData(
            id=uuid.uuid4(),
            sku_id=incoming.sku_id,
            process_id=incoming.process_id,
            param_key=incoming.param_key,
            param_value=incoming.param_value,
            unit_price=incoming.unit_price,
            currency=incoming.currency,
            supplier=incoming.supplier,
            quote_date=incoming.quote_date,
            source=incoming.source,
            target_layer=incoming.target_layer,
            client_id=incoming.client_id,
            batch_id=batch_id,
            is_test_batch=True,
        )
        db.add(verified)
        count += 1

    await db.flush()
    return count


async def recalculate_benchmarks(
    db: AsyncSession,
    process_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Recompute avg_price, std_dev, and sample_size for each (process_id, param_key)
    group in VerifiedBusinessData and upsert into ProcessBenchmark.

    Args:
        db: async DB session
        process_ids: optional list of process_ids to restrict the recalculation.
                     If None, all process_ids are recalculated.

    Returns:
        dict mapping process_id -> list of updated stat dicts
    """
    # Query VerifiedBusinessData
    conditions = []
    if process_ids:
        conditions.append(VerifiedBusinessData.process_id.in_(process_ids))

    stmt = select(VerifiedBusinessData)
    if conditions:
        stmt = stmt.where(and_(*conditions))

    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    # Group by (process_id, param_key)
    groups: dict[tuple, list[float]] = {}
    for row in rows:
        key = (row.process_id, row.param_key)
        groups.setdefault(key, []).append(row.unit_price)

    updated: dict[str, list[dict]] = {}

    for (process_id, param_key), prices in groups.items():
        n = len(prices)
        avg = sum(prices) / n
        if n > 1:
            variance = sum((p - avg) ** 2 for p in prices) / (n - 1)
            std = math.sqrt(variance)
        else:
            std = 0.0

        # Determine source_type (all test data = "external"; could be extended later)
        source_type = "external"

        # Upsert: find existing benchmark for this (process_id, param_key)
        existing_result = await db.execute(
            select(ProcessBenchmark).where(
                and_(
                    ProcessBenchmark.process_id == process_id,
                    ProcessBenchmark.param_key == param_key,
                )
            ).limit(1)
        )
        existing = existing_result.scalar_one_or_none()

        if existing is not None:
            existing.avg_price = avg
            existing.std_dev = std
            existing.sample_size = n
            existing.source_type = source_type
            existing.last_calculated_at = datetime.now(timezone.utc)
        else:
            benchmark = ProcessBenchmark(
                id=uuid.uuid4(),
                process_id=process_id,
                param_key=param_key,
                avg_price=avg,
                std_dev=std,
                sample_size=n,
                source_type=source_type,
                currency="CNY",
                last_calculated_at=datetime.now(timezone.utc),
            )
            db.add(benchmark)

        stat = {
            "param_key": param_key,
            "avg_price": avg,
            "std_dev": std,
            "sample_size": n,
            "source_type": source_type,
        }
        updated.setdefault(process_id, []).append(stat)

    await db.flush()
    return updated


async def get_test_batch_summary(
    db: AsyncSession,
    batch_id: str,
) -> dict[str, Any]:
    """
    Return a summary of a test batch: total record count, sample_size per
    process_id, and source_type distribution.

    Args:
        db: async DB session
        batch_id: the batch identifier used in submit_test_batch

    Returns:
        dict with keys: batch_id, total_records, process_breakdown (dict),
        source_distribution (dict)
    """
    result = await db.execute(
        select(VerifiedBusinessData).where(
            VerifiedBusinessData.batch_id == batch_id
        )
    )
    rows = list(result.scalars().all())

    total = len(rows)

    # sample_size per process_id
    process_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}

    for row in rows:
        process_counts[row.process_id] = process_counts.get(row.process_id, 0) + 1
        src = row.source or "unknown"
        source_counts[src] = source_counts.get(src, 0) + 1

    return {
        "batch_id": batch_id,
        "total_records": total,
        "process_breakdown": process_counts,
        "source_distribution": source_counts,
    }
