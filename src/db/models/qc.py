"""
SQLAlchemy ORM models for QC reference images, process cards, and comparison reports.
Only active when GIRAFFE_DB_MODE=on.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Float, Boolean, Integer, Text, DateTime, ForeignKey, func
from src.db.json_type import PortableJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base


class QCReferenceImageORM(Base):
    __tablename__ = "qc_reference_images"

    ref_image_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    milestone_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)


class QCProcessCardORM(Base):
    __tablename__ = "qc_process_cards"

    process_card_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    material_spec: Mapped[str | None] = mapped_column(Text, nullable=True)
    color_spec: Mapped[str | None] = mapped_column(String(256), nullable=True)
    size_spec: Mapped[str | None] = mapped_column(Text, nullable=True)
    finish_spec: Mapped[str | None] = mapped_column(String(256), nullable=True)
    defect_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    supplier_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)
    updated_at: Mapped[str] = mapped_column(String(32), nullable=False)


class QCComparisonReportORM(Base):
    __tablename__ = "qc_comparison_reports"

    report_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    milestone_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    overall_result: Mapped[str] = mapped_column(String(32), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(32), nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    requested_provider: Mapped[str] = mapped_column(String(32), nullable=False)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False)
    m_side_feedback_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    m_side_feedback_en: Mapped[str] = mapped_column(Text, nullable=False, default="")
    b_side_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    image_count: Mapped[int] = mapped_column(Integer, default=0)
    frames_used: Mapped[int] = mapped_column(Integer, default=0)
    buyer_confirmation_required: Mapped[bool] = mapped_column(Boolean, default=False)
    saved_at: Mapped[str] = mapped_column(String(32), nullable=False)


class QCStandard(Base):
    __tablename__ = "qc_standards"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), unique=True, nullable=False)
    measurement_tolerance: Mapped[dict] = mapped_column(JSONB, nullable=True)
    fabric_defect_limits: Mapped[dict] = mapped_column(JSONB, nullable=True)
    stitching_standards: Mapped[dict] = mapped_column(JSONB, nullable=True)
    color_difference_tolerance: Mapped[dict] = mapped_column(JSONB, nullable=True)
    size_deviation_limits: Mapped[dict] = mapped_column(JSONB, nullable=True)
    washing_requirements: Mapped[dict] = mapped_column(JSONB, nullable=True)
    label_requirements: Mapped[dict] = mapped_column(JSONB, nullable=True)
    packaging_requirements: Mapped[dict] = mapped_column(JSONB, nullable=True)
    compliance_notes: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class QCRecord(Base):
    __tablename__ = "qc_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    qc_standard_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("qc_standards.id"), nullable=True)
    inspector_participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=True)
    measurement_results: Mapped[dict] = mapped_column(JSONB, nullable=True)
    fabric_defects: Mapped[dict] = mapped_column(JSONB, nullable=True)
    stitching_defects: Mapped[dict] = mapped_column(JSONB, nullable=True)
    color_difference: Mapped[dict] = mapped_column(JSONB, nullable=True)
    size_deviation: Mapped[dict] = mapped_column(JSONB, nullable=True)
    washing_result: Mapped[dict] = mapped_column(JSONB, nullable=True)
    label_compliance: Mapped[bool] = mapped_column(Boolean, nullable=True)
    packaging_compliance: Mapped[bool] = mapped_column(Boolean, nullable=True)
    photo_evidence_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)
    inspection_report_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)
    result: Mapped[str] = mapped_column(String(50), default="QC_PENDING")
    rework_required: Mapped[bool] = mapped_column(Boolean, default=False)
    responsible_participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=True)
    inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
