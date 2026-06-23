from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GPMEvidenceReference:
    """A reference to a single piece of pricing evidence used in a GPMContextBundle."""

    id: str
    source_type: str  # api_sample | supplier_quote | historical_order | private_record | manual_fixture
    source_id: str
    source_platform: str | None = None
    title: str | None = None
    observed_at: datetime | None = None
    payload_excerpt: dict | None = None
    raw_payload_hash: str | None = None
    usable_for_analysis: bool = True
    invalid_reasons: list[str] = field(default_factory=list)
