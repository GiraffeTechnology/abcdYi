from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional
import uuid


class ParticipantCreate(BaseModel):
    name: str
    company_registration: Optional[str] = None
    country: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class ParticipantUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None


class ParticipantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    country: Optional[str]
    contact_email: Optional[str]
    is_active: bool
    profile_completeness_score: float


class RoleAssign(BaseModel):
    role_name: str


class RoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    role_name: str
    is_active: bool
