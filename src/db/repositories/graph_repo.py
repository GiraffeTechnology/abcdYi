from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from src.db.models.procurement_edge import ProcurementEdge
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class GraphRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_edge(
        self,
        project_id: str,
        from_actor_id: str,
        to_actor_id: str,
        edge_type: str,
        parent_edge_id: Optional[str] = None,
        inquiry_id: Optional[str] = None,
        response_id: Optional[str] = None,
        status: str = "DRAFT",
        metadata_json: Optional[dict] = None,
        edge_id: Optional[str] = None,
    ) -> ProcurementEdge:
        now = _utcnow()
        edge = ProcurementEdge(
            edge_id=edge_id or new_uuid(),
            project_id=project_id,
            from_actor_id=from_actor_id,
            to_actor_id=to_actor_id,
            edge_type=edge_type,
            parent_edge_id=parent_edge_id,
            inquiry_id=inquiry_id,
            response_id=response_id,
            status=status,
            created_at=now,
            updated_at=now,
            metadata_json=metadata_json or {},
        )
        self.db.add(edge)
        self.db.flush()
        return edge

    def get_project_edges(self, project_id: str) -> List[ProcurementEdge]:
        return self.db.query(ProcurementEdge).filter(
            ProcurementEdge.project_id == project_id
        ).all()

    def get_child_edges(self, parent_edge_id: str) -> List[ProcurementEdge]:
        return self.db.query(ProcurementEdge).filter(
            ProcurementEdge.parent_edge_id == parent_edge_id
        ).all()

    def get_edge(self, edge_id: str) -> Optional[ProcurementEdge]:
        return self.db.query(ProcurementEdge).filter(
            ProcurementEdge.edge_id == edge_id
        ).first()

    def update_edge_status(self, edge_id: str, status: str) -> Optional[ProcurementEdge]:
        edge = self.get_edge(edge_id)
        if edge:
            edge.status = status
            edge.updated_at = _utcnow()
            self.db.flush()
        return edge
