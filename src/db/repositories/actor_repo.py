from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from src.db.models.actor import Actor
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class ActorRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_actor(
        self,
        name: str,
        actor_type: str,
        default_language: Optional[str] = None,
        contact_channels_json: Optional[dict] = None,
        capabilities_json: Optional[dict] = None,
        profile_json: Optional[dict] = None,
        is_active: bool = True,
        actor_id: Optional[str] = None,
    ) -> Actor:
        now = _utcnow()
        actor = Actor(
            actor_id=actor_id or new_uuid(),
            name=name,
            actor_type=actor_type,
            default_language=default_language,
            contact_channels_json=contact_channels_json or {},
            capabilities_json=capabilities_json or {},
            profile_json=profile_json or {},
            is_active=is_active,
            created_at=now,
            updated_at=now,
        )
        self.db.add(actor)
        self.db.flush()
        return actor

    def get_actor(self, actor_id: str) -> Optional[Actor]:
        return self.db.query(Actor).filter(Actor.actor_id == actor_id).first()

    def list_actors(self, actor_type: Optional[str] = None, is_active: Optional[bool] = None):
        q = self.db.query(Actor)
        if actor_type is not None:
            q = q.filter(Actor.actor_type == actor_type)
        if is_active is not None:
            q = q.filter(Actor.is_active == is_active)
        return q.all()
