"""Explicit user/project permissions; roles never come from request headers."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from src.db.base import Base


class ProjectMembership(Base):
    __tablename__ = 'project_memberships'
    __table_args__ = (UniqueConstraint('project_id', 'user_id', name='uq_project_member'),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('projects.id'), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    participant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('participants.id'), nullable=True)
    granted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey('users.id'), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
