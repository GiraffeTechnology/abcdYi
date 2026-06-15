import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models.project import ProcurementEdge


async def get_contextual_role(
    db: AsyncSession,
    participant_id: uuid.UUID,
    project_id: uuid.UUID,
) -> str | None:
    """
    Returns the role a participant plays in a specific project edge.
    The same company can play different roles in different project edges.
    """
    result = await db.execute(
        select(ProcurementEdge).where(
            ProcurementEdge.project_id == project_id,
            ProcurementEdge.participant_id == participant_id,
        )
    )
    edge = result.scalar_one_or_none()
    return edge.contextual_role if edge else None
