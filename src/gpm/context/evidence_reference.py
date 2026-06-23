from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field as PydanticField


@dataclass
class GPMEvidenceReference:
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


class EvidenceReference(BaseModel):
    """Pydantic evidence reference for structured GPM context bundles."""

    evidence_id: str
    source_type: Literal[
        "public_api",
        "authorized_marketplace_api",
        "csv_import",
        "excel_import",
        "private_erp",
        "private_supplier_quote",
        "private_historical_order",
        "supplier_email",
        "manual_upload",
        "system_generated_quote",
        "system_generated_order",
        "system_generated_execution_event",
    ]
    visibility: Literal[
        "public_benchmark",
        "tenant_private",
        "internal_system",
        "restricted",
    ]
    source_label: Optional[str] = None
    observed_at: Optional[datetime] = None
    captured_at: Optional[datetime] = None
    payload: dict[str, Any] = PydanticField(default_factory=dict)
