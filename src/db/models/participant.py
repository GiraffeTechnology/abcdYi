import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Float, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.db.base import Base

class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_registration: Mapped[str] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    profile_completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ParticipantRole(Base):
    __tablename__ = "participant_roles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=False)
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ParticipantProfile(Base):
    __tablename__ = "participant_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), unique=True, nullable=False)
    product_categories: Mapped[dict] = mapped_column(JSONB, nullable=True)
    fabric_capabilities: Mapped[dict] = mapped_column(JSONB, nullable=True)
    quantity_range_min: Mapped[int] = mapped_column(Integer, nullable=True)
    quantity_range_max: Mapped[int] = mapped_column(Integer, nullable=True)
    moq: Mapped[int] = mapped_column(Integer, nullable=True)
    lead_time_days_min: Mapped[int] = mapped_column(Integer, nullable=True)
    lead_time_days_max: Mapped[int] = mapped_column(Integer, nullable=True)
    supported_trade_terms: Mapped[dict] = mapped_column(JSONB, nullable=True)
    supported_countries: Mapped[dict] = mapped_column(JSONB, nullable=True)
    certifications: Mapped[dict] = mapped_column(JSONB, nullable=True)
    languages: Mapped[dict] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class ParticipantCapability(Base):
    __tablename__ = "participant_capabilities"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=False)
    capability_type: Mapped[str] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class ParticipantPermission(Base):
    __tablename__ = "participant_permissions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(nullable=True)
    permission_name: Mapped[str] = mapped_column(String(100), nullable=False)
    granted_by: Mapped[uuid.UUID] = mapped_column(nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
