from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from src.db.models.inquiry import SupplierInquiry
from src.db.models.upstream import UpstreamInquiry
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class InquiryRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_supplier_inquiry(
        self,
        project_id: str,
        edge_id: str,
        from_actor_id: str,
        to_actor_id: str,
        requirement_id: Optional[str] = None,
        message_text_en: Optional[str] = None,
        message_text_zh: Optional[str] = None,
        message_text_local: Optional[str] = None,
        requested_fields_json: Optional[dict] = None,
        required_reply_schema_json: Optional[dict] = None,
        status: str = "SENT",
        inquiry_id: Optional[str] = None,
    ) -> SupplierInquiry:
        now = _utcnow()
        inq = SupplierInquiry(
            inquiry_id=inquiry_id or new_uuid(),
            project_id=project_id,
            edge_id=edge_id,
            from_actor_id=from_actor_id,
            to_actor_id=to_actor_id,
            requirement_id=requirement_id,
            message_text_en=message_text_en,
            message_text_zh=message_text_zh,
            message_text_local=message_text_local,
            requested_fields_json=requested_fields_json or {},
            required_reply_schema_json=required_reply_schema_json or {},
            status=status,
            created_at=now,
            updated_at=now,
        )
        self.db.add(inq)
        self.db.flush()
        return inq

    def create_upstream_inquiry(
        self,
        project_id: str,
        edge_id: str,
        dependency_id: str,
        parent_main_supplier_actor_id: str,
        upstream_actor_id: str,
        message_text_en: Optional[str] = None,
        message_text_zh: Optional[str] = None,
        requested_fields_json: Optional[dict] = None,
        required_reply_schema_json: Optional[dict] = None,
        due_time: Optional[str] = None,
        dispatch_channel: Optional[str] = None,
        status: str = "SENT",
        upstream_inquiry_id: Optional[str] = None,
    ) -> UpstreamInquiry:
        now = _utcnow()
        inq = UpstreamInquiry(
            upstream_inquiry_id=upstream_inquiry_id or new_uuid(),
            project_id=project_id,
            edge_id=edge_id,
            dependency_id=dependency_id,
            parent_main_supplier_actor_id=parent_main_supplier_actor_id,
            upstream_actor_id=upstream_actor_id,
            message_text_en=message_text_en,
            message_text_zh=message_text_zh,
            requested_fields_json=requested_fields_json or {},
            required_reply_schema_json=required_reply_schema_json or {},
            due_time=due_time,
            dispatch_channel=dispatch_channel,
            status=status,
            created_at=now,
            updated_at=now,
        )
        self.db.add(inq)
        self.db.flush()
        return inq
