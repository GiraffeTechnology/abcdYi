"""
abcdyi ↔ GPM proxy routes.

The frontend calls these endpoints to get benchmark data with sample_size
and source_type visible (spec §2.1 and §5 requirement).
abcdyi never exposes GPM internals — it only proxies read queries.
"""
from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_current_user
from src.gpm.client import get_benchmarks, validate_price, check_missing_processes
from src.gpm.schemas import (
    ProcessBenchmarkOut,
    PriceValidationRequest,
    PriceValidationResult,
    MissingProcessCheckRequest,
    MissingProcessAlert,
)

# All routes require a valid logged-in user — same standard as all other tenant-facing APIs.
router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/benchmarks", response_model=list[ProcessBenchmarkOut])
async def query_gpm_benchmarks(
    process_id: str | None = Query(None, description="Filter by process ID"),
    sku_id: str | None = Query(None, description="Filter by SKU ID"),
):
    """
    Returns benchmark records including avg_price, std_dev, sample_size, and source_type.
    Frontend MUST display sample_size and source_type alongside the price figure.
    """
    try:
        return await get_benchmarks(process_id=process_id, sku_id=sku_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"GPM service unavailable: {exc}")


@router.post("/benchmarks/validate", response_model=PriceValidationResult)
async def validate_quoted_price(body: PriceValidationRequest):
    """
    Validates a quoted unit price against GPM benchmarks.
    Returns VALID / NEEDS_REVIEW / EXCLUDED / NO_BENCHMARK classification.
    """
    try:
        return await validate_price(
            process_id=body.process_id,
            unit_price=body.unit_price,
            currency=body.currency,
            sku_id=body.sku_id,
            param_key=body.param_key,
            param_value=body.param_value,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"GPM service unavailable: {exc}")


@router.post("/processes/missing-check", response_model=MissingProcessAlert)
async def check_missing_gpm_processes(body: MissingProcessCheckRequest):
    """
    Checks whether all processes expected for a SKU are present in the quote.
    Returns a list of missing process IDs with an advisory message.
    """
    try:
        return await check_missing_processes(
            sku_id=body.sku_id,
            declared_process_ids=body.declared_process_ids,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"GPM service unavailable: {exc}")
