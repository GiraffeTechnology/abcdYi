from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from src.db.models.execution_event import ExecutionEvent
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class ExecutionEventRepo:
    def __init__(self, db: Session):
        self.db = db

    def log_event(
        self,
        event_type: str,
        project_id: Optional[str] = None,
        edge_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        role_context_id: Optional[str] = None,
        payload_json: Optional[dict] = None,
        source_channel: Optional[str] = None,
        source_message_id: Optional[str] = None,
        confidence_score: Optional[float] = None,
        metadata_json: Optional[dict] = None,
        event_id: Optional[str] = None,
    ) -> ExecutionEvent:
        now = _utcnow()
        event = ExecutionEvent(
            event_id=event_id or new_uuid(),
            project_id=project_id,
            edge_id=edge_id,
            actor_id=actor_id,
            role_context_id=role_context_id,
            event_type=event_type,
            payload_json=payload_json or {},
            source_channel=source_channel,
            source_message_id=source_message_id,
            confidence_score=confidence_score,
            created_at=now,
            metadata_json=metadata_json or {},
        )
        self.db.add(event)
        self.db.flush()
        return event

    def list_project_events(self, project_id: str) -> List[ExecutionEvent]:
        return self.db.query(ExecutionEvent).filter(
            ExecutionEvent.project_id == project_id
        ).order_by(ExecutionEvent.created_at).all()

    def list_events_by_type(self, event_type: str, project_id: Optional[str] = None) -> List[ExecutionEvent]:
        q = self.db.query(ExecutionEvent).filter(ExecutionEvent.event_type == event_type)
        if project_id:
            q = q.filter(ExecutionEvent.project_id == project_id)
        return q.order_by(ExecutionEvent.created_at).all()
