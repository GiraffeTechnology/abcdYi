import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class RFQ(Base):
    __tablename__ = "rfqs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    form_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dynamic_order_form_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    rfq_content: Mapped[dict] = mapped_column(JSONB, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    human_approved_by: Mapped[uuid.UUID] = mapped_column(nullable=True)
    human_approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class RFQRecipient(Base):
    __tablename__ = "rfq_recipients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rfq_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rfqs.id"), nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    responded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")

class SupplierResponse(Base):
    __tablename__ = "supplier_responses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rfq_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rfqs.id"), nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=False)
    raw_response_text: Mapped[str] = mapped_column(Text, nullable=True)
    raw_response_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class SupplierResponsePacket(Base):
    __tablename__ = "supplier_response_packets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    supplier_response_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("supplier_responses.id"), unique=True, nullable=False)
    unit_price: Mapped[float] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=True)
    moq: Mapped[int] = mapped_column(Integer, nullable=True)
    sample_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    fabric_lead_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    trim_lead_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    production_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    qc_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    packaging_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    logistics_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    total_lead_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    payment_terms: Mapped[str] = mapped_column(String(255), nullable=True)
    trade_terms: Mapped[str] = mapped_column(String(100), nullable=True)
    capacity_available: Mapped[int] = mapped_column(Integer, nullable=True)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    supplier_notes: Mapped[str] = mapped_column(Text, nullable=True)
    missing_fields: Mapped[dict] = mapped_column(JSONB, nullable=True)
    risk_flags: Mapped[dict] = mapped_column(JSONB, nullable=True)
    evidence_source: Mapped[dict] = mapped_column(JSONB, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    human_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
