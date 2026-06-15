import uuid
from datetime import date, datetime
from sqlalchemy import String, DateTime, Date, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base


class DeliveryFeasibilityPacketRecord(Base):
    __tablename__ = "delivery_feasibility_packets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=True)
    order_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="GLTG")
    status: Mapped[str] = mapped_column(String(50), default="EVALUATED")
    # Overall delivery dates (from best feasible path)
    earliest_delivery_date: Mapped[date] = mapped_column(Date, nullable=True)
    most_likely_delivery_date: Mapped[date] = mapped_column(Date, nullable=True)
    risk_adjusted_delivery_date: Mapped[date] = mapped_column(Date, nullable=True)
    committable_delivery_date: Mapped[date] = mapped_column(Date, nullable=True)
    required_delivery_date: Mapped[date] = mapped_column(Date, nullable=True)
    # Feasibility verdict
    delivery_feasibility: Mapped[str] = mapped_column(String(50), default="UNKNOWN")
    days_vs_deadline: Mapped[int] = mapped_column(Integer, nullable=True)
    # Critical path summary
    critical_path_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    critical_path_days: Mapped[int] = mapped_column(Integer, nullable=True)
    # Ranked options (up to 3, serialised from GLTG DeliveryPath objects)
    ranked_options_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    option_count: Mapped[int] = mapped_column(Integer, default=0)
    # Risk and evidence
    risk_flags_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    missing_evidence_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    # Raw GLTG output preserved for debugging / re-evaluation
    raw_gltg_packet_json: Mapped[dict] = mapped_column(JSONB, nullable=True)
    # Human-readable explanation from GLTG engine
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), default="LOW")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
