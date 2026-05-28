from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from src.db.models.role_context import RoleContext
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class RoleRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_role_context(
        self,
        project_id: str,
        actor_id: str,
        role: str,
        edge_id: Optional[str] = None,
        counterparty_actor_id: Optional[str] = None,
        role_reason: str = "",
        permissions_json: Optional[dict] = None,
        can_create_upstream_inquiry: bool = False,
        can_approve_upstream_option: bool = False,
        can_submit_response_to_buyer: bool = False,
        metadata_json: Optional[dict] = None,
        role_context_id: Optional[str] = None,
    ) -> RoleContext:
        now = _utcnow()
        rc = RoleContext(
            role_context_id=role_context_id or new_uuid(),
            project_id=project_id,
            edge_id=edge_id,
            actor_id=actor_id,
            counterparty_actor_id=counterparty_actor_id,
            role=role,
            role_reason=role_reason,
            permissions_json=permissions_json or {},
            can_create_upstream_inquiry=can_create_upstream_inquiry,
            can_approve_upstream_option=can_approve_upstream_option,
            can_submit_response_to_buyer=can_submit_response_to_buyer,
            created_at=now,
            metadata_json=metadata_json or {},
        )
        self.db.add(rc)
        self.db.flush()
        return rc

    def resolve_role_context(
        self,
        project_id: str,
        actor_id: str,
        edge_id: Optional[str] = None,
    ) -> Optional[RoleContext]:
        q = self.db.query(RoleContext).filter(
            RoleContext.project_id == project_id,
            RoleContext.actor_id == actor_id,
        )
        if edge_id:
            q = q.filter(RoleContext.edge_id == edge_id)
        return q.first()

    def list_actor_roles_in_project(self, project_id: str, actor_id: str) -> List[RoleContext]:
        return self.db.query(RoleContext).filter(
            RoleContext.project_id == project_id,
            RoleContext.actor_id == actor_id,
        ).all()
