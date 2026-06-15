import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models.execution_graph import ExecutionEvent
from src.execution_graph import event_types


async def emit_event(
    db: AsyncSession,
    event_type: str,
    payload: dict,
    tenant_id: uuid.UUID,
    project_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    participant_id: uuid.UUID | None = None,
    triggered_by_user_id: uuid.UUID | None = None,
) -> ExecutionEvent:
    event = ExecutionEvent(
        tenant_id=tenant_id,
        project_id=project_id,
        order_id=order_id,
        participant_id=participant_id,
        event_type=event_type,
        payload=payload,
        triggered_by_user_id=triggered_by_user_id,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()
    return event
