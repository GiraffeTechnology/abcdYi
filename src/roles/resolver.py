from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from src.db.models.procurement_edge import ProcurementEdge


async def get_contextual_role(
    db: AsyncSession,
    actor_id: str,
    project_id: str,
) -> str | None:
    """
    Returns the edge_type an actor plays in a specific project edge.
    The same actor can play different roles in different project edges.
    """
    result = await db.execute(
        select(ProcurementEdge).where(
            ProcurementEdge.project_id == project_id,
            or_(
                ProcurementEdge.from_actor_id == actor_id,
                ProcurementEdge.to_actor_id == actor_id,
            ),
        )
    )
    edge = result.scalar_one_or_none()
    return edge.edge_type if edge else None
