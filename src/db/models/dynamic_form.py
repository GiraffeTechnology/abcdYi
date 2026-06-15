import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base

class DynamicOrderForm(Base):
    __tablename__ = "dynamic_order_forms"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), unique=True, nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class DynamicOrderFormVersion(Base):
    __tablename__ = "dynamic_order_form_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dynamic_order_forms.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    fields: Mapped[dict] = mapped_column(JSONB, nullable=False)
    ai_generated_fields: Mapped[dict] = mapped_column(JSONB, nullable=True)
    human_confirmed_fields: Mapped[dict] = mapped_column(JSONB, nullable=True)
    missing_fields: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ClarificationQuestion(Base):
    __tablename__ = "clarification_questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("dynamic_order_forms.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    field_reference: Mapped[str] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="OPEN")
    answer_text: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
