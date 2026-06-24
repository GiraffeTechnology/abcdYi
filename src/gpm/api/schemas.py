from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class QuoteGuidanceRequest(BaseModel):
    tenant_id: str | None = None
    project_id: str | None = None
    rfq_id: str | None = None
    supplier_response_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    include_private_data: bool = True
    operator_id: str | None = None
    runtime_mode: str | None = None
    request_context: dict = Field(default_factory=dict)


class ApprovalRequest(BaseModel):
    operator_id: str
    approval_status: Literal["approved"] = "approved"
    approval_note: str = ""
    selected_option_id: str | None = None


class RejectionRequest(BaseModel):
    operator_id: str
    approval_status: Literal["rejected"] = "rejected"
    approval_note: str = ""


class ApprovalRecord(BaseModel):
    packet_id: str
    operator_id: str
    approval_status: str
    approval_note: str = ""
    selected_option_id: str | None = None
    recorded_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    dispatched: bool = False
    dispatch_note: str = "No external action taken."
