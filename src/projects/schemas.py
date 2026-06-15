from pydantic import BaseModel, ConfigDict
from typing import Optional
import uuid
from datetime import datetime


class ProjectCreate(BaseModel):
    title: str
    notes: Optional[str] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    status: str
    created_at: datetime


class BuyerInquiryCreate(BaseModel):
    buyer_participant_id: Optional[uuid.UUID] = None
    raw_text: str
    source_channel: Optional[str] = "manual"


class BuyerInquiryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    raw_text: Optional[str]
    source_channel: Optional[str]
    received_at: datetime
