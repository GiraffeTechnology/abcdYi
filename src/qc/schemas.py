import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class QCStandardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    measurement_tolerance: Optional[dict]
    fabric_defect_limits: Optional[dict]
    size_deviation_limits: Optional[dict]
    label_requirements: Optional[dict]
    packaging_requirements: Optional[dict]
    created_at: datetime


class QCRecordCreate(BaseModel):
    inspector_participant_id: Optional[uuid.UUID] = None
    measurement_results: Optional[dict] = None
    fabric_defects: Optional[dict] = None
    stitching_defects: Optional[dict] = None
    color_difference: Optional[dict] = None
    size_deviation: Optional[dict] = None
    washing_result: Optional[dict] = None
    label_compliance: Optional[bool] = None
    packaging_compliance: Optional[bool] = None
    photo_evidence_metadata: Optional[dict] = None
    inspection_report_metadata: Optional[dict] = None
    responsible_participant_id: Optional[uuid.UUID] = None


class QCRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    result: str
    rework_required: bool
    responsible_participant_id: Optional[uuid.UUID]
    inspected_at: Optional[datetime]
    created_at: datetime
