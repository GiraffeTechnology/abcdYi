from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from src.db.models.requirement import StructuredRequirement
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class RequirementRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_requirement(
        self,
        project_id: str,
        source_actor_id: str,
        source_message_id: Optional[str] = None,
        raw_input_refs_json: Optional[dict] = None,
        category: Optional[str] = None,
        quantity: Optional[int] = None,
        material: Optional[str] = None,
        specs_json: Optional[dict] = None,
        deadline: Optional[str] = None,
        destination: Optional[str] = None,
        missing_fields_json: Optional[dict] = None,
        confidence_score: float = 0.0,
        requirement_id: Optional[str] = None,
    ) -> StructuredRequirement:
        now = _utcnow()
        req = StructuredRequirement(
            requirement_id=requirement_id or new_uuid(),
            project_id=project_id,
            source_actor_id=source_actor_id,
            source_message_id=source_message_id,
            raw_input_refs_json=raw_input_refs_json or {},
            category=category,
            quantity=quantity,
            material=material,
            specs_json=specs_json or {},
            deadline=deadline,
            destination=destination,
            missing_fields_json=missing_fields_json or {},
            confidence_score=confidence_score,
            created_at=now,
            updated_at=now,
        )
        self.db.add(req)
        self.db.flush()
        return req
