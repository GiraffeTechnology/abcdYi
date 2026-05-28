from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from src.db.models.project import Project
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class ProjectRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_project(
        self,
        original_buyer_actor_id: str,
        main_supplier_actor_id: Optional[str] = None,
        category: Optional[str] = None,
        product_summary: Optional[str] = None,
        quantity: Optional[int] = None,
        status: str = "CREATED",
        product_tier: str = "free",
        created_by_channel: Optional[str] = None,
        metadata_json: Optional[dict] = None,
        project_id: Optional[str] = None,
    ) -> Project:
        now = _utcnow()
        project = Project(
            project_id=project_id or new_uuid(),
            original_buyer_actor_id=original_buyer_actor_id,
            main_supplier_actor_id=main_supplier_actor_id,
            category=category,
            product_summary=product_summary,
            quantity=quantity,
            status=status,
            product_tier=product_tier,
            created_by_channel=created_by_channel,
            created_at=now,
            updated_at=now,
            metadata_json=metadata_json or {},
        )
        self.db.add(project)
        self.db.flush()
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        return self.db.query(Project).filter(Project.project_id == project_id).first()

    def update_project_status(self, project_id: str, status: str) -> Optional[Project]:
        project = self.get_project(project_id)
        if project:
            project.status = status
            project.updated_at = _utcnow()
            self.db.flush()
        return project
