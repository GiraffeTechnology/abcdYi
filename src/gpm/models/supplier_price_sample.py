from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class GPMSupplierPriceSample:
    id: str

    source_platform: str
    source_offer_id: str | None

    supplier_id: str | None
    supplier_name: str | None
    supplier_location: str | None

    captured_at: datetime | None
    observed_at: datetime | None

    product_title: str
    product_url: str | None
    image_url: str | None

    category_id: str | None
    category_name: str | None

    material: str | None
    process_tags: list[str]
    customization_supported: bool | None

    price_min: Decimal | None
    price_max: Decimal | None
    price_currency: str
    price_unit: str

    moq: Decimal | None
    moq_unit: str | None

    ladder_prices: list[dict]
    sku_attributes: dict

    delivery_region: str | None
    lead_time_text: str | None

    raw_response_id: str

    created_at: datetime

    # Set by validate_sample(); not constructor parameters
    usable_for_benchmark: bool = field(default=False, init=False)
    usable_for_quote_guidance: bool = field(default=False, init=False)
    invalid_reasons: list[str] = field(default_factory=list, init=False)
