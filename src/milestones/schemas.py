import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class MilestoneUpdate(BaseModel):
    status: Optional[str] = None
    actual_date: Optional[datetime] = None
    predicted_date: Optional[datetime] = None
    notes: Optional[str] = None
    responsible_participant_id: Optional[uuid.UUID] = None


class ProductionUpdateCreate(BaseModel):
    milestone_id: Optional[uuid.UUID] = None
    update_text: str
    submitted_by_participant_id: Optional[uuid.UUID] = None
    evidence: Optional[dict] = None


class MilestoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    milestone_type: str
    planned_date: Optional[datetime]
    predicted_date: Optional[datetime]
    actual_date: Optional[datetime]
    status: str
    responsible_participant_id: Optional[uuid.UUID]
    notes: Optional[str]
