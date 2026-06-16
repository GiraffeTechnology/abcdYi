"""
abcdyi → GPM HTTP client.

abcdyi calls GPM only via this client — never via direct DB access.
The client enforces the read/write split:
  - read path: benchmark queries, price validation, missing-process check
  - write path: submit order data to incoming_order_data buffer ONLY
"""
import logging
import os
from typing import Any

import httpx

from src.gpm.schemas import (
    ProcessBenchmarkOut,
    PriceValidationRequest,
    PriceValidationResult,
    MissingProcessCheckRequest,
    MissingProcessAlert,
    IncomingOrderDataCreate,
    IncomingOrderDataOut,
)

logger = logging.getLogger(__name__)

_GPM_SERVICE_URL = os.environ.get("GPM_SERVICE_URL", "http://localhost:8001")
_GPM_API_KEY = os.environ.get("GPM_SERVICE_API_KEY", "")
_TIMEOUT = 10.0  # seconds


def _headers() -> dict[str, str]:
    return {"X-GPM-API-Key": _GPM_API_KEY, "Content-Type": "application/json"}


async def get_benchmarks(
    process_id: str | None = None,
    sku_id: str | None = None,
) -> list[ProcessBenchmarkOut]:
    params: dict[str, str] = {}
    if process_id:
        params["process_id"] = process_id
    if sku_id:
        params["sku_id"] = sku_id

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.get(
            f"{_GPM_SERVICE_URL}/gpm/v1/benchmarks",
            headers=_headers(),
            params=params,
        )
        response.raise_for_status()
        return [ProcessBenchmarkOut(**item) for item in response.json()]


async def validate_price(
    process_id: str,
    unit_price: float,
    currency: str = "USD",
    sku_id: str | None = None,
    param_key: str | None = None,
    param_value: str | None = None,
) -> PriceValidationResult:
    payload = PriceValidationRequest(
        process_id=process_id,
        unit_price=unit_price,
        currency=currency,
        sku_id=sku_id,
        param_key=param_key,
        param_value=param_value,
    )
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            f"{_GPM_SERVICE_URL}/gpm/v1/benchmarks/validate",
            headers=_headers(),
            content=payload.model_dump_json(),
        )
        response.raise_for_status()
        return PriceValidationResult(**response.json())


async def check_missing_processes(
    sku_id: str,
    declared_process_ids: list[str],
) -> MissingProcessAlert:
    payload = MissingProcessCheckRequest(
        sku_id=sku_id,
        declared_process_ids=declared_process_ids,
    )
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(
            f"{_GPM_SERVICE_URL}/gpm/v1/processes/missing-check",
            headers=_headers(),
            content=payload.model_dump_json(),
        )
        response.raise_for_status()
        return MissingProcessAlert(**response.json())


async def submit_order_to_buffer(
    payload: IncomingOrderDataCreate,
) -> IncomingOrderDataOut | None:
    """
    Push order pricing data to GPM's incoming_order_data buffer.
    Returns None silently on failure — GPM unavailability must never block order flow.
    """
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(
                f"{_GPM_SERVICE_URL}/gpm/v1/incoming-orders",
                headers=_headers(),
                content=payload.model_dump_json(),
            )
            response.raise_for_status()
            return IncomingOrderDataOut(**response.json())
    except Exception as exc:
        logger.warning("GPM buffer submission failed for order %s: %s", payload.order_id, exc)
        return None
