"""
B-side workspace persistence — in-memory + JSON file storage.
Data is stored under data/b_side_workspaces/.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.core_schema.b_side_types import BWWorkspace

_DATA_DIR = Path("data/b_side_workspaces")


def _ensure_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _workspace_path(b_workspace_id: str) -> Path:
    return _DATA_DIR / f"{b_workspace_id}.json"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_b_workspace(raw_requirement: str) -> BWWorkspace:
    """Create a new B-side workspace and persist it."""
    _ensure_dir()
    b_workspace_id = f"bw_{uuid.uuid4().hex[:12]}"
    rfq_id = f"RFQ-{uuid.uuid4().hex[:8].upper()}"
    now = _utcnow()
    workspace = BWWorkspace(
        b_workspace_id=b_workspace_id,
        rfq_id=rfq_id,
        raw_requirement=raw_requirement,
        status="created",
        created_at=now,
        updated_at=now,
    )
    return save_b_workspace(workspace)


def get_b_workspace(b_workspace_id: str) -> BWWorkspace:
    """Load a persisted B-side workspace by ID."""
    _ensure_dir()
    path = _workspace_path(b_workspace_id)
    if not path.exists():
        raise FileNotFoundError(f"B-side workspace not found: {b_workspace_id}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return BWWorkspace.model_validate(data)


def save_b_workspace(workspace: BWWorkspace) -> BWWorkspace:
    """Persist B-side workspace and update updated_at."""
    _ensure_dir()
    workspace.updated_at = _utcnow()
    path = _workspace_path(workspace.b_workspace_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(workspace.model_dump(mode="json"), f, ensure_ascii=False, indent=2)
    return workspace


def update_b_workspace_status(b_workspace_id: str, status: str) -> BWWorkspace:
    """Update B-side workspace status and persist."""
    workspace = get_b_workspace(b_workspace_id)
    workspace.status = status
    return save_b_workspace(workspace)
