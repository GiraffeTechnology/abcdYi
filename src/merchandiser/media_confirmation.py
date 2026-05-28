"""
Media evidence — links uploaded media to milestones for buyer review.
Persisted under data/merchandiser/media/.
"""
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from src.m_side.m_event_logger import log_m_event

_DATA_DIR = Path("data/merchandiser/media")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class MediaEvidence(BaseModel):
    media_id: str
    project_id: str
    milestone_id: str
    uploaded_by_actor_id: str
    artifact_id: str | None = None
    media_type: Literal["image", "video", "document", "shipping_label"]
    description: str | None = None
    visibility_check_status: Literal["pass", "fail", "unknown"] = "pass"
    completeness_check_status: Literal["pass", "fail", "unknown"] = "pass"
    buyer_review_status: Literal["pending", "confirmed", "rejected", "not_required"] = "pending"
    notes: str | None = None
    created_at: str = Field(default_factory=_utcnow)


def upload_media_evidence(
    project_id: str,
    milestone_id: str,
    uploaded_by_actor_id: str,
    media_type: str = "image",
    description: str | None = None,
    artifact_id: str | None = None,
    count: int = 1,
) -> list[MediaEvidence]:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    evidences = []
    for i in range(count):
        ev = MediaEvidence(
            media_id=f"MEDIA-{uuid.uuid4().hex[:10].upper()}",
            project_id=project_id,
            milestone_id=milestone_id,
            uploaded_by_actor_id=uploaded_by_actor_id,
            artifact_id=artifact_id,
            media_type=media_type,  # type: ignore[arg-type]
            description=description or f"Media upload {i+1}/{count}",
            buyer_review_status="pending" if media_type != "shipping_label" else "not_required",
        )
        path = _DATA_DIR / f"{ev.media_id}.json"
        path.write_text(ev.model_dump_json(indent=2), encoding="utf-8")
        evidences.append(ev)

    log_m_event(
        event_type="ORDER_MILESTONE_MEDIA_UPLOADED",
        b_workspace_id=project_id,
        payload={
            "milestone_id": milestone_id,
            "uploaded_by": uploaded_by_actor_id,
            "count": count,
            "media_type": media_type,
        },
    )
    return evidences
