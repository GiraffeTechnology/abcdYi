import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Text, Integer, JSON, func
from src.db.json_type import PortableJSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base
from src.db.mixins import new_uuid

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="OPEN")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Actor-based (M-side / GLTG) project identity, used by the role-switching
    # / upstream-sourcing schema in parallel with the UUID `id` PK above.
    project_id: Mapped[str | None] = mapped_column(String(36), unique=True, nullable=True, default=new_uuid)
    original_buyer_actor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    main_supplier_actor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("actors.actor_id"), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    product_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_tier: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_by_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, default=dict, nullable=True)

class BuyerInquiry(Base):
    __tablename__ = "buyer_inquiries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    buyer_participant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("participants.id"), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)
    raw_files_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True)
    source_channel: Mapped[str] = mapped_column(String(100), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class RawMessage(Base):
    __tablename__ = "raw_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    inquiry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("buyer_inquiries.id"), nullable=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    sender: Mapped[str] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    msg_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
