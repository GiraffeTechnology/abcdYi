from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


@dataclass
class GPMQuoteGuidance:
    benchmark_snapshot_id: str
    supplier_quote_price: Decimal
    supplier_quote_currency: str
    supplier_quote_unit: str
    supplier_quote_position: str
    accept_recommendation: str
    explanation: str
    margin_policy: dict
    risk_flags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requirement_id: str | None = None
    supplier_id: str | None = None
    supplier_quote_moq: Decimal | None = None
    recommended_counter_price: Decimal | None = None
    recommended_buyer_quote_low: Decimal | None = None
    recommended_buyer_quote_mid: Decimal | None = None
    recommended_buyer_quote_high: Decimal | None = None
    human_approval_required: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
