import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    milestone_type: Mapped[str] = mapped_column(String(100), nullable=False)
    planned_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    predicted_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    responsible_participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ProductionUpdate(Base):
    __tablename__ = "production_updates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    milestone_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("milestones.id"), nullable=True)
    update_text: Mapped[str] = mapped_column(Text, nullable=True)
    submitted_by_participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=True)
    evidence: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ProductionMonitoringPacket(Base):
    __tablename__ = "production_monitoring_packets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    standard_completion_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    predicted_completion_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    delay_risk_level: Mapped[str] = mapped_column(String(50), nullable=True)
    responsible_participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=True)
    delayed_milestones: Mapped[dict] = mapped_column(JSONB, nullable=True)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=True)
    expedite_alert_required: Mapped[bool] = mapped_column(Boolean, default=False)
    human_approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ExpediteAlert(Base):
    __tablename__ = "expedite_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    monitoring_packet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("production_monitoring_packets.id"), nullable=True)
    target_participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=True)
    alert_message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT")
    human_approved_by: Mapped[uuid.UUID] = mapped_column(nullable=True)
    human_approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
