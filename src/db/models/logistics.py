"""SQLAlchemy ORM models for Logistics."""
from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, Index, JSON, Text
from src.db.base import Base
import uuid
from datetime import datetime, timezone


def _new_uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


class LogisticsShipmentORM(Base):
    __tablename__ = "logistics_shipments"
    shipment_id = Column(String(36), primary_key=True, default=_new_uuid)
    project_id = Column(String(36), nullable=True, index=True)
    order_id = Column(String(36), nullable=True, index=True)
    provider_name = Column(String(64), nullable=True)
    provider_shipment_id = Column(String(128), nullable=True)
    carrier_name = Column(String(64), nullable=True)
    carrier_code = Column(String(16), nullable=True)
    tracking_number = Column(String(128), nullable=False, index=True)
    sender_actor_id = Column(String(36), nullable=True)
    receiver_actor_id = Column(String(36), nullable=True)
    origin = Column(String(256), nullable=True)
    destination = Column(String(256), nullable=True)
    current_status = Column(String(32), default="label_created")
    estimated_delivery_date = Column(DateTime, nullable=True)
    actual_delivery_date = Column(DateTime, nullable=True)
    last_event_at = Column(DateTime, nullable=True)
    last_synced_at = Column(DateTime, nullable=True)
    sync_status = Column(String(32), nullable=True)
    sync_error = Column(Text, nullable=True)
    polling_enabled = Column(Boolean, default=True)
    webhook_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    metadata_json = Column(JSON, default=dict)


class LogisticsEventORM(Base):
    __tablename__ = "logistics_events"
    logistics_event_id = Column(String(36), primary_key=True, default=_new_uuid)
    shipment_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=True, index=True)
    provider_name = Column(String(64), nullable=True)
    provider_event_id = Column(String(128), nullable=True)
    carrier_name = Column(String(64), nullable=True)
    tracking_number = Column(String(128), nullable=True)
    event_time = Column(DateTime, nullable=True)
    status = Column(String(64), nullable=True)
    raw_status_code = Column(String(64), nullable=True)
    normalized_status = Column(String(32), nullable=True, index=True)
    location = Column(String(256), nullable=True)
    description = Column(Text, nullable=True)
    raw_payload_json = Column(JSON, default=dict)
    source = Column(String(32), nullable=True)
    event_hash = Column(String(64), nullable=True, index=True)
    is_duplicate = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    metadata_json = Column(JSON, default=dict)
