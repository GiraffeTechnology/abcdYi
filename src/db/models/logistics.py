import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Float, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class QualityIncident(Base):
    __tablename__ = "quality_incidents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    qc_record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("qc_records.id"), nullable=True)
    responsible_participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ReplacementAlert(Base):
    __tablename__ = "replacement_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=True)
    trigger_reason: Mapped[str] = mapped_column(Text, nullable=False)
    quality_issue_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING_REVIEW")
    reviewed_by: Mapped[uuid.UUID] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    logistics_provider_participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=True)
    carrier: Mapped[str] = mapped_column(String(255), nullable=True)
    tracking_number: Mapped[str] = mapped_column(String(255), nullable=True)
    trade_term: Mapped[str] = mapped_column(String(50), nullable=True)
    origin: Mapped[str] = mapped_column(String(255), nullable=True)
    destination: Mapped[str] = mapped_column(String(255), nullable=True)
    estimated_departure_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    estimated_arrival_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_departure_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_arrival_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    logistics_risk_flags: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ShipmentTrackingEvent(Base):
    __tablename__ = "shipment_tracking_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shipment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shipments.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SupplierMemoryRecord(Base):
    __tablename__ = "supplier_memory_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=False)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=True)
    on_time_delivery: Mapped[bool] = mapped_column(Boolean, nullable=True)
    qc_pass_rate: Mapped[float] = mapped_column(Float, nullable=True)
    response_time_hours: Mapped[float] = mapped_column(Float, nullable=True)
    price_competitiveness: Mapped[float] = mapped_column(Float, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
