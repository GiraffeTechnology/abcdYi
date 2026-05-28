"""
B-side core Pydantic v2 models for Giraffe Agent AI Buyer.
"""

from datetime import datetime, timezone
from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BuyerRequirement(BaseModel):
    rfq_id: str
    b_workspace_id: str
    raw_text: str
    category: str | None = None
    quantity: int | None = None
    material: str | None = None
    specs_json: dict = Field(default_factory=dict)
    deadline: str | None = None
    destination: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    created_at: datetime = Field(default_factory=_utcnow)


class SupplierInquiryDraft(BaseModel):
    rfq_id: str
    b_workspace_id: str
    inquiry_id: str
    supplier_ids: list[str] = Field(default_factory=list)
    message_text_en: str = ""
    message_text_zh: str = ""
    required_fields: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)


class SupplierResponseRecord(BaseModel):
    response_id: str
    rfq_id: str
    b_workspace_id: str
    supplier_id: str
    supplier_name: str
    can_make: bool | None = None
    capacity_available: bool | None = None
    material_available: bool | None = None
    estimated_lead_time_days: int | None = None
    unit_price: float | None = None
    total_price: float | None = None
    currency: str | None = None
    qc_available: bool | None = None
    logistics_notes: str | None = None
    red_flags: list[str] = Field(default_factory=list)
    completeness_score: float = 0.0
    confidence_score: float = 0.0
    raw_response: str = ""
    submitted_at: datetime = Field(default_factory=_utcnow)


class DeliveryPath(BaseModel):
    path_id: str
    rfq_id: str
    supplier_id: str
    supplier_name: str
    lead_time_days: int | None = None
    unit_price: float | None = None
    currency: str | None = None
    total_price: float | None = None
    risk_score: float = 0.0
    confidence_score: float = 0.0
    notes: str | None = None
    rank: int = 0


class FeasibilityReport(BaseModel):
    rfq_id: str
    b_workspace_id: str
    paths: list[DeliveryPath] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_utcnow)
    selected_path_id: str | None = None


class BWWorkspace(BaseModel):
    b_workspace_id: str
    rfq_id: str
    raw_requirement: str = ""
    buyer_requirement: BuyerRequirement | None = None
    supplier_inquiry_draft: SupplierInquiryDraft | None = None
    supplier_responses: list[SupplierResponseRecord] = Field(default_factory=list)
    feasibility_report: FeasibilityReport | None = None
    status: str = "created"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
