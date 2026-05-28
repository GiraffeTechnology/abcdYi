from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from src.db.models.rollup import SupplierResponseRollup
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)


class RollupRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_rollup(
        self,
        project_id: str,
        main_supplier_actor_id: str,
        can_accept_order: Optional[bool] = None,
        main_capacity_summary: Optional[str] = None,
        approved_upstream_options_json: Optional[dict] = None,
        material_basis_json: Optional[dict] = None,
        trim_basis_json: Optional[dict] = None,
        subcontract_basis_json: Optional[dict] = None,
        qc_basis_json: Optional[dict] = None,
        packaging_basis_json: Optional[dict] = None,
        logistics_basis_json: Optional[dict] = None,
        price_basis_json: Optional[dict] = None,
        lead_time_basis_json: Optional[dict] = None,
        unresolved_dependencies_json: Optional[dict] = None,
        risk_flags_json: Optional[dict] = None,
        completeness_score: float = 0.0,
        confidence_score: float = 0.0,
        recommended_response_to_buyer_en: Optional[str] = None,
        recommended_response_to_buyer_zh: Optional[str] = None,
        cad_requirement_packet_id: Optional[str] = None,
        cad_cnc_match_id: Optional[str] = None,
        capability_fit_report_id: Optional[str] = None,
        cnc_parameter_match_summary_json: Optional[dict] = None,
        can_make_in_house: Optional[bool] = None,
        recommended_machine_ids_json: Optional[dict] = None,
        capability_gaps_json: Optional[dict] = None,
        upstream_dependency_basis_json: Optional[dict] = None,
        rollup_id: Optional[str] = None,
    ) -> SupplierResponseRollup:
        now = _utcnow()
        rollup = SupplierResponseRollup(
            rollup_id=rollup_id or new_uuid(),
            project_id=project_id,
            main_supplier_actor_id=main_supplier_actor_id,
            can_accept_order=can_accept_order,
            main_capacity_summary=main_capacity_summary,
            approved_upstream_options_json=approved_upstream_options_json or {},
            material_basis_json=material_basis_json or {},
            trim_basis_json=trim_basis_json or {},
            subcontract_basis_json=subcontract_basis_json or {},
            qc_basis_json=qc_basis_json or {},
            packaging_basis_json=packaging_basis_json or {},
            logistics_basis_json=logistics_basis_json or {},
            price_basis_json=price_basis_json or {},
            lead_time_basis_json=lead_time_basis_json or {},
            unresolved_dependencies_json=unresolved_dependencies_json or {},
            risk_flags_json=risk_flags_json or {},
            completeness_score=completeness_score,
            confidence_score=confidence_score,
            recommended_response_to_buyer_en=recommended_response_to_buyer_en,
            recommended_response_to_buyer_zh=recommended_response_to_buyer_zh,
            cad_requirement_packet_id=cad_requirement_packet_id,
            cad_cnc_match_id=cad_cnc_match_id,
            capability_fit_report_id=capability_fit_report_id,
            cnc_parameter_match_summary_json=cnc_parameter_match_summary_json or {},
            can_make_in_house=can_make_in_house,
            recommended_machine_ids_json=recommended_machine_ids_json or {},
            capability_gaps_json=capability_gaps_json or {},
            upstream_dependency_basis_json=upstream_dependency_basis_json or {},
            created_at=now,
            updated_at=now,
        )
        self.db.add(rollup)
        self.db.flush()
        return rollup

    def get_rollup(self, rollup_id: str) -> Optional[SupplierResponseRollup]:
        return self.db.query(SupplierResponseRollup).filter(
            SupplierResponseRollup.rollup_id == rollup_id
        ).first()

    def get_project_rollup(self, project_id: str) -> Optional[SupplierResponseRollup]:
        return self.db.query(SupplierResponseRollup).filter(
            SupplierResponseRollup.project_id == project_id
        ).first()
