"""
Pydantic schemas for the abcdyi ↔ GPM API contract.
These mirror the GPM service's schemas and are used by the abcdyi client.
"""
import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel


class ProcessBenchmarkOut(BaseModel):
    id: uuid.UUID
    process_id: str
    sku_id: str | None
    param_key: str | None
    param_value: str | None
    avg_price: float
    std_dev: float | None
    sample_size: int
    source_type: str  # "internal" | "external" | "mixed"
    currency: str
    last_calculated_at: datetime


class PriceValidationRequest(BaseModel):
    process_id: str
    unit_price: float
    currency: str = "USD"
    sku_id: str | None = None
    param_key: str | None = None
    param_value: str | None = None


class PriceValidationResult(BaseModel):
    process_id: str
    unit_price: float
    avg_price: float | None
    std_dev: float | None
    sample_size: int | None
    source_type: str | None
    deviation_rate: float | None
    classification: Literal["VALID", "NEEDS_REVIEW", "EXCLUDED", "NO_BENCHMARK"]
    benchmark_found: bool


class MissingProcessCheckRequest(BaseModel):
    sku_id: str
    declared_process_ids: list[str]


class MissingProcessAlert(BaseModel):
    sku_id: str
    missing_process_ids: list[str]
    message: str


class IncomingOrderDataCreate(BaseModel):
    order_id: str
    sku_id: str | None = None
    process_id: str
    param_key: str | None = None
    param_value: str | None = None
    unit_price: float
    currency: str = "USD"
    supplier: str | None = None
    quote_date: datetime | None = None
    source: str | None = None
    target_layer: Literal["universal", "client_proprietary"] = "universal"
    client_id: str | None = None


class IncomingOrderDataOut(BaseModel):
    id: uuid.UUID
    order_id: str
    process_id: str
    unit_price: float
    currency: str
    review_status: str
    target_layer: str
    written_at: datetime
