from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


@dataclass
class GPMBenchmarkSnapshot:
    query_keyword: str
    source_platform: str
    sample_count: int
    comparable_sample_count: int
    excluded_sample_count: int
    confidence_level: str
    confidence_reason: str
    normalized_process_tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requirement_id: str | None = None
    normalized_product_type: str | None = None
    normalized_material: str | None = None
    benchmark_low: Decimal | None = None
    benchmark_median: Decimal | None = None
    benchmark_high: Decimal | None = None
    weighted_median: Decimal | None = None
    target_quantity: Decimal | None = None
    target_quantity_unit: str | None = None
    captured_from: datetime | None = None
    captured_to: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
