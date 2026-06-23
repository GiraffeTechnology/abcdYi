from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class PricingQuery:
    keyword: str
    product_type: str | None = None
    material: str | None = None
    process_tags: list[str] = field(default_factory=list)
    target_quantity: Decimal | None = None
    target_unit: str | None = None
    region_filter: str | None = None
    max_samples: int = 50
    source_platform: str = "1688"
