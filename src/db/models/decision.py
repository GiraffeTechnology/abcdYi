import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Float, Integer, Text, func
from src.db.json_type import PortableJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class DecisionPacket(Base):
    __tablename__ = "decision_packets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    comparison_summary: Mapped[str] = mapped_column(Text, nullable=True)
    risk_summary: Mapped[str] = mapped_column(Text, nullable=True)
    missing_field_summary: Mapped[str] = mapped_column(Text, nullable=True)
    human_approval_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    recommended_option_id: Mapped[uuid.UUID] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class DecisionOption(Base):
    __tablename__ = "decision_options"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    packet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("decision_packets.id"), nullable=False)
    option_index: Mapped[int] = mapped_column(Integer, nullable=False)
    supplier_combination: Mapped[dict] = mapped_column(JSONB, nullable=True)
    unit_price: Mapped[float] = mapped_column(Float, nullable=True)
    total_price: Mapped[float] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=True)
    lead_time_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=True)
    calculated_total_lead_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    supplier_stated_lead_time_days: Mapped[int] = mapped_column(Integer, nullable=True)
    risk_flags: Mapped[dict] = mapped_column(JSONB, nullable=True)
    missing_fields: Mapped[dict] = mapped_column(JSONB, nullable=True)
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[uuid.UUID] = mapped_column(nullable=True)
    proposed_payload: Mapped[dict] = mapped_column(JSONB, nullable=True)
    affected_participant_id: Mapped[uuid.UUID] = mapped_column(nullable=True)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=True)
    risk_flags: Mapped[dict] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    reviewed_by: Mapped[uuid.UUID] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    review_notes: Mapped[str] = mapped_column(Text, nullable=True)
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
