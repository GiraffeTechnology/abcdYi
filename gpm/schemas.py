import uuid
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


# ── Read path: benchmark query responses ──────────────────────────────────────

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

    class Config:
        from_attributes = True


class DeviationClassification(str):
    VALID = "VALID"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    EXCLUDED = "EXCLUDED"


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


# ── Write path: incoming order data ──────────────────────────────────────────

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
    sku_id: str | None
    process_id: str
    param_key: str | None
    param_value: str | None
    unit_price: float
    currency: str
    supplier: str | None
    quote_date: datetime | None
    source: str | None
    review_status: str
    target_layer: str
    client_id: str | None
    written_at: datetime
    reviewed_at: datetime | None
    reviewed_by: str | None
    review_notes: str | None
    auto_confirmed: bool

    class Config:
        from_attributes = True


class ReviewDecision(BaseModel):
    decision: Literal["CONFIRMED", "REJECTED"]
    reviewer_id: str
    notes: str | None = None


class AutoReviewResult(BaseModel):
    processed: int
    auto_confirmed: int
    pending_human_review: int
    excluded: int
