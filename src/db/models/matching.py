import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Float, Text, func
from src.db.json_type import PortableJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class ParticipantMatch(Base):
    __tablename__ = "participant_matches"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=False)
    recommended_role: Mapped[str] = mapped_column(String(100), nullable=False)
    match_score: Mapped[float] = mapped_column(Float, nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSONB, nullable=True)
    matched_requirements: Mapped[dict] = mapped_column(JSONB, nullable=True)
    unmatched_requirements: Mapped[dict] = mapped_column(JSONB, nullable=True)
    risk_flags: Mapped[dict] = mapped_column(JSONB, nullable=True)
    missing_participant_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=True)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
