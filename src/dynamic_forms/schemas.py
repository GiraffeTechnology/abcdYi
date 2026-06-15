from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
import uuid
from datetime import datetime


class DynamicFormCreateRequest(BaseModel):
    inquiry_id: uuid.UUID


class DynamicFormFieldUpdate(BaseModel):
    field_updates: dict[str, Any]
    confirmed_fields: list[str] = []


class ClarificationQuestionCreate(BaseModel):
    question_text: str
    field_reference: Optional[str] = None


class DynamicFormVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    form_id: uuid.UUID
    version_number: int
    fields: dict
    ai_generated_fields: list
    human_confirmed_fields: list
    missing_fields: list
    created_at: datetime


class DynamicFormOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    project_id: uuid.UUID
    current_version: int
    is_locked: bool
    created_at: datetime
