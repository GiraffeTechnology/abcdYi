"""SQLAlchemy ORM models for AI Merchandiser."""
import json
from sqlalchemy import Column, String, Boolean, Integer, Float, DateTime, Index, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from src.db.base import Base
import uuid
from datetime import datetime, timezone


def _new_uuid():
    return str(uuid.uuid4())


def _utcnow():
    return datetime.now(timezone.utc)


class MerchandiserExecutionPlan(Base):
    __tablename__ = "merchandiser_execution_plans"
    plan_id = Column(String(36), primary_key=True, default=_new_uuid)
    project_id = Column(String(36), nullable=True, index=True)
    order_id = Column(String(36), nullable=True, index=True)
    supplier_actor_id = Column(String(36), nullable=True)
    buyer_actor_id = Column(String(36), nullable=True)
    category = Column(String(64), nullable=True)
    current_order_state = Column(String(64), nullable=True)
    task_ids_json = Column(JSON, default=list)
    milestone_ids_json = Column(JSON, default=list)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    metadata_json = Column(JSON, default=dict)


class MerchandiserTask(Base):
    __tablename__ = "merchandiser_tasks"
    task_id = Column(String(36), primary_key=True, default=_new_uuid)
    project_id = Column(String(36), nullable=True, index=True)
    order_id = Column(String(36), nullable=True)
    assigned_side = Column(String(32), nullable=True)
    assigned_actor_id = Column(String(36), nullable=True)
    role_context_id = Column(String(36), nullable=True)
    task_type = Column(String(64), nullable=True, index=True)
    due_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="PENDING", index=True)
    priority = Column(String(16), default="medium")
    payload_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    metadata_json = Column(JSON, default=dict)


class OrderMilestoneORM(Base):
    __tablename__ = "order_milestones"
    milestone_id = Column(String(36), primary_key=True, default=_new_uuid)
    project_id = Column(String(36), nullable=True, index=True)
    order_id = Column(String(36), nullable=True)
    milestone_type = Column(String(64), nullable=True)
    sequence_no = Column(Integer, default=0)
    expected_at = Column(DateTime, nullable=True)
    actual_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="PENDING")
    evidence_required = Column(Boolean, default=True)
    required_media_types_json = Column(JSON, default=list)
    assigned_actor_id = Column(String(36), nullable=True)
    buyer_confirmation_required = Column(Boolean, default=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class MediaEvidenceORM(Base):
    __tablename__ = "media_evidence"
    media_id = Column(String(36), primary_key=True, default=_new_uuid)
    project_id = Column(String(36), nullable=True, index=True)
    milestone_id = Column(String(36), nullable=True, index=True)
    uploaded_by_actor_id = Column(String(36), nullable=True)
    artifact_id = Column(String(36), nullable=True)
    media_type = Column(String(32), nullable=True)
    description = Column(Text, nullable=True)
    visibility_check_status = Column(String(16), default="unknown")
    completeness_check_status = Column(String(16), default="unknown")
    buyer_review_status = Column(String(32), default="pending")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    metadata_json = Column(JSON, default=dict)


class OrderExceptionORM(Base):
    __tablename__ = "order_exceptions"
    exception_id = Column(String(36), primary_key=True, default=_new_uuid)
    project_id = Column(String(36), nullable=True, index=True)
    order_id = Column(String(36), nullable=True)
    raised_by_actor_id = Column(String(36), nullable=True)
    exception_type = Column(String(64), nullable=True)
    severity = Column(String(16), default="medium")
    description = Column(Text, nullable=True)
    proposed_options_json = Column(JSON, default=list)
    buyer_confirmation_required = Column(Boolean, default=False)
    human_review_required = Column(Boolean, default=False)
    status = Column(String(32), default="OPEN")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)
    metadata_json = Column(JSON, default=dict)
