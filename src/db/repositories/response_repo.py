from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from src.db.models.response import SupplierResponse
from src.db.models.upstream import UpstreamResponse, UpstreamOption
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class ResponseRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_supplier_response(
        self,
        project_id: str,
        edge_id: str,
        from_actor_id: str,
        to_actor_id: str,
        inquiry_id: Optional[str] = None,
        can_supply: Optional[bool] = None,
        price: Optional[float] = None,
        currency: Optional[str] = None,
        moq: Optional[float] = None,
        available_quantity: Optional[float] = None,
        lead_time_days: Optional[int] = None,
        earliest_dispatch_date: Optional[str] = None,
        capacity_basis_json: Optional[dict] = None,
        material_basis_json: Optional[dict] = None,
        subcontract_basis_json: Optional[dict] = None,
        qc_basis_json: Optional[dict] = None,
        logistics_basis_json: Optional[dict] = None,
        risk_flags_json: Optional[dict] = None,
        raw_message: Optional[str] = None,
        parsed_json: Optional[dict] = None,
        confidence_score: float = 0.0,
        completeness_score: float = 0.0,
        response_id: Optional[str] = None,
    ) -> SupplierResponse:
        now = _utcnow()
        resp = SupplierResponse(
            response_id=response_id or new_uuid(),
            project_id=project_id,
            edge_id=edge_id,
            inquiry_id=inquiry_id,
            from_actor_id=from_actor_id,
            to_actor_id=to_actor_id,
            can_supply=can_supply,
            price=price,
            currency=currency,
            moq=moq,
            available_quantity=available_quantity,
            lead_time_days=lead_time_days,
            earliest_dispatch_date=earliest_dispatch_date,
            capacity_basis_json=capacity_basis_json or {},
            material_basis_json=material_basis_json or {},
            subcontract_basis_json=subcontract_basis_json or {},
            qc_basis_json=qc_basis_json or {},
            logistics_basis_json=logistics_basis_json or {},
            risk_flags_json=risk_flags_json or {},
            raw_message=raw_message,
            parsed_json=parsed_json or {},
            confidence_score=confidence_score,
            completeness_score=completeness_score,
            created_at=now,
            updated_at=now,
        )
        self.db.add(resp)
        self.db.flush()
        return resp

    def create_upstream_response(
        self,
        project_id: str,
        edge_id: str,
        upstream_inquiry_id: str,
        dependency_id: str,
        from_actor_id: str,
        can_supply: bool = False,
        matched_specs_json: Optional[dict] = None,
        price: Optional[float] = None,
        currency: Optional[str] = None,
        moq: Optional[float] = None,
        available_quantity: Optional[float] = None,
        lead_time_days: Optional[int] = None,
        earliest_dispatch_date: Optional[str] = None,
        quality_notes: Optional[str] = None,
        substitute_options_json: Optional[dict] = None,
        risk_flags_json: Optional[dict] = None,
        confidence_score: float = 0.0,
        completeness_score: float = 0.0,
        raw_message: Optional[str] = None,
        upstream_response_id: Optional[str] = None,
    ) -> UpstreamResponse:
        now = _utcnow()
        resp = UpstreamResponse(
            upstream_response_id=upstream_response_id or new_uuid(),
            project_id=project_id,
            edge_id=edge_id,
            upstream_inquiry_id=upstream_inquiry_id,
            dependency_id=dependency_id,
            from_actor_id=from_actor_id,
            can_supply=can_supply,
            matched_specs_json=matched_specs_json or {},
            price=price,
            currency=currency,
            moq=moq,
            available_quantity=available_quantity,
            lead_time_days=lead_time_days,
            earliest_dispatch_date=earliest_dispatch_date,
            quality_notes=quality_notes,
            substitute_options_json=substitute_options_json or {},
            risk_flags_json=risk_flags_json or {},
            confidence_score=confidence_score,
            completeness_score=completeness_score,
            raw_message=raw_message,
            created_at=now,
            updated_at=now,
        )
        self.db.add(resp)
        self.db.flush()
        return resp

    def create_upstream_option(
        self,
        project_id: str,
        dependency_id: str,
        upstream_actor_id: str,
        option_label: str,
        score: float = 0.0,
        price_summary: Optional[str] = None,
        lead_time_summary: Optional[str] = None,
        risk_summary: Optional[str] = None,
        reason: Optional[str] = None,
        response_ids_json: Optional[dict] = None,
        status: str = "pending",
        option_id: Optional[str] = None,
    ) -> UpstreamOption:
        now = _utcnow()
        opt = UpstreamOption(
            option_id=option_id or new_uuid(),
            project_id=project_id,
            dependency_id=dependency_id,
            upstream_actor_id=upstream_actor_id,
            option_label=option_label,
            score=score,
            price_summary=price_summary,
            lead_time_summary=lead_time_summary,
            risk_summary=risk_summary,
            reason=reason,
            response_ids_json=response_ids_json or {},
            status=status,
            created_at=now,
            updated_at=now,
        )
        self.db.add(opt)
        self.db.flush()
        return opt
