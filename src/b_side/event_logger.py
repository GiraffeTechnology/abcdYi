"""
B-side event logger — logs events to the SQLite Industrial Execution Graph.
"""

from src.db.session import SessionLocal
from src.db.repositories.execution_event_repo import ExecutionEventRepo


def log_b_event(event_type: str, b_workspace_id: str, payload: dict) -> None:
    """
    Log a B-side event to the Industrial Execution Graph (SQLite execution_events table).
    """
    db = SessionLocal()
    try:
        repo = ExecutionEventRepo(db)
        repo.log_event(
            event_type=event_type,
            payload_json={
                "b_workspace_id": b_workspace_id,
                **payload,
            },
            source_channel="b_side",
        )
        db.commit()
    except Exception as e:
        db.rollback()
        # Non-fatal — log to stderr but don't crash the workflow
        import sys
        print(f"[B-side event logger] WARNING: Failed to log event {event_type}: {e}", file=sys.stderr)
    finally:
        db.close()
