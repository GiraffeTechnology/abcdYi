import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class ShipmentCreate(BaseModel):
    logistics_provider_participant_id: Optional[uuid.UUID] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    trade_term: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    estimated_departure_date: Optional[datetime] = None
    estimated_arrival_date: Optional[datetime] = None


class TrackingEventCreate(BaseModel):
    event_type: str
    location: Optional[str] = None
    description: Optional[str] = None
    occurred_at: datetime


class ShipmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    carrier: Optional[str]
    tracking_number: Optional[str]
    trade_term: Optional[str]
    origin: Optional[str]
    destination: Optional[str]
    estimated_departure_date: Optional[datetime]
    estimated_arrival_date: Optional[datetime]
    actual_departure_date: Optional[datetime]
    actual_arrival_date: Optional[datetime]
    logistics_risk_flags: Optional[list]
    created_at: datetime
