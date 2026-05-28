from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from src.db.models.cad_cnc import CADRequirementPacket, ManufacturingFeatureSet, CADCNCMatchResult, CapabilityFitReport
from src.db.models.capability import ShopCapabilityProfile
from src.db.models.artifact import Artifact
from src.db.mixins import new_uuid


def _utcnow():
    return datetime.now(timezone.utc)

PROFESSIONAL_FREE_WARNING = (
    "Professional Free does not provide encrypted file protection or Enterprise CAP. "
    "Do not upload highly confidential CAD / STEP / BOM files. "
    "Use Enterprise CAP for confidential engineering documents."
)


class CADCNCRepo:
    def __init__(self, db: Session):
        self.db = db

    def create_artifact(
        self,
        file_ref: str,
        artifact_type: str,
        project_id: Optional[str] = None,
        owner_actor_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_hash: Optional[str] = None,
        mime_type: Optional[str] = None,
        size_bytes: Optional[int] = None,
        metadata_json: Optional[dict] = None,
        product_tier: str = "professional_free",
        warning_acknowledged: bool = False,
        artifact_id: Optional[str] = None,
    ) -> Artifact:
        now = _utcnow()
        art = Artifact(
            artifact_id=artifact_id or new_uuid(),
            project_id=project_id,
            owner_actor_id=owner_actor_id,
            artifact_type=artifact_type,
            file_name=file_name,
            file_ref=file_ref,
            file_hash=file_hash,
            mime_type=mime_type,
            size_bytes=size_bytes,
            metadata_json=metadata_json or {},
            product_tier=product_tier,
            cap_level=None,
            encryption_enabled=False,
            dynamic_watermark_enabled=False,
            secure_viewer_enabled=False,
            warning_acknowledged=warning_acknowledged,
            created_at=now,
            updated_at=now,
        )
        self.db.add(art)
        self.db.flush()
        return art

    def create_cad_requirement_packet(
        self,
        project_id: str,
        original_buyer_actor_id: str,
        artifact_id: str,
        main_supplier_actor_id: Optional[str] = None,
        part_summary: Optional[str] = None,
        material: Optional[str] = None,
        quantity: Optional[int] = None,
        dimensions_json: Optional[dict] = None,
        tolerance_requirements_json: Optional[dict] = None,
        surface_finish_requirements_json: Optional[dict] = None,
        thread_requirements_json: Optional[dict] = None,
        heat_treatment_requirements_json: Optional[dict] = None,
        operation_requirements_json: Optional[dict] = None,
        qc_requirements_json: Optional[dict] = None,
        packaging_requirements_json: Optional[dict] = None,
        delivery_deadline: Optional[str] = None,
        missing_information_json: Optional[dict] = None,
        extraction_confidence_score: float = 0.0,
        packet_id: Optional[str] = None,
    ) -> CADRequirementPacket:
        # Verify warning acknowledged for professional_free artifacts
        artifact = self.db.query(Artifact).filter(Artifact.artifact_id == artifact_id).first()
        if artifact and artifact.product_tier == "professional_free" and not artifact.warning_acknowledged:
            raise ValueError(PROFESSIONAL_FREE_WARNING)

        now = _utcnow()
        packet = CADRequirementPacket(
            packet_id=packet_id or new_uuid(),
            project_id=project_id,
            original_buyer_actor_id=original_buyer_actor_id,
            main_supplier_actor_id=main_supplier_actor_id,
            file_refs_json={"artifact_id": artifact_id},
            source_types_json={},
            part_summary=part_summary,
            material=material,
            quantity=quantity,
            dimensions_json=dimensions_json or {},
            tolerance_requirements_json=tolerance_requirements_json or {},
            surface_finish_requirements_json=surface_finish_requirements_json or {},
            thread_requirements_json=thread_requirements_json or {},
            heat_treatment_requirements_json=heat_treatment_requirements_json or {},
            operation_requirements_json=operation_requirements_json or {},
            qc_requirements_json=qc_requirements_json or {},
            packaging_requirements_json=packaging_requirements_json or {},
            delivery_deadline=delivery_deadline,
            missing_information_json=missing_information_json or {},
            extraction_confidence_score=extraction_confidence_score,
            created_at=now,
            updated_at=now,
        )
        self.db.add(packet)
        self.db.flush()
        return packet

    def create_shop_capability_profile(
        self,
        actor_id: str,
        profile_name: Optional[str] = None,
        machines_json: Optional[dict] = None,
        tooling_inventory_json: Optional[dict] = None,
        qc_equipment_json: Optional[dict] = None,
        material_inventory_json: Optional[dict] = None,
        in_house_processes_json: Optional[dict] = None,
        outsourced_processes_json: Optional[dict] = None,
        schedule_summary_json: Optional[dict] = None,
        profile_id: Optional[str] = None,
    ) -> ShopCapabilityProfile:
        now = _utcnow()
        profile = ShopCapabilityProfile(
            profile_id=profile_id or new_uuid(),
            actor_id=actor_id,
            profile_name=profile_name,
            machines_json=machines_json or {},
            tooling_inventory_json=tooling_inventory_json or {},
            qc_equipment_json=qc_equipment_json or {},
            material_inventory_json=material_inventory_json or {},
            in_house_processes_json=in_house_processes_json or {},
            outsourced_processes_json=outsourced_processes_json or {},
            schedule_summary_json=schedule_summary_json or {},
            created_at=now,
            updated_at=now,
        )
        self.db.add(profile)
        self.db.flush()
        return profile

    def create_match_result(
        self,
        project_id: str,
        actor_id: str,
        cad_requirement_packet_id: str,
        shop_capability_profile_id: str,
        can_make_in_house: bool = False,
        recommended_machine_ids_json: Optional[dict] = None,
        machine_fit_score: float = 0.0,
        work_envelope_fit: str = "unknown",
        material_fit: str = "unknown",
        tolerance_fit: str = "unknown",
        surface_finish_fit: str = "unknown",
        tooling_fit: str = "unknown",
        qc_fit: str = "unknown",
        schedule_fit: str = "unknown",
        required_upstream_dependencies_json: Optional[dict] = None,
        required_subcontract_dependencies_json: Optional[dict] = None,
        risk_flags_json: Optional[dict] = None,
        missing_information_json: Optional[dict] = None,
        confidence_score: float = 0.0,
        explanation: Optional[str] = None,
        match_id: Optional[str] = None,
    ) -> CADCNCMatchResult:
        now = _utcnow()
        result = CADCNCMatchResult(
            match_id=match_id or new_uuid(),
            project_id=project_id,
            actor_id=actor_id,
            cad_requirement_packet_id=cad_requirement_packet_id,
            shop_capability_profile_id=shop_capability_profile_id,
            can_make_in_house=can_make_in_house,
            recommended_machine_ids_json=recommended_machine_ids_json or {},
            machine_fit_score=machine_fit_score,
            work_envelope_fit=work_envelope_fit,
            material_fit=material_fit,
            tolerance_fit=tolerance_fit,
            surface_finish_fit=surface_finish_fit,
            tooling_fit=tooling_fit,
            qc_fit=qc_fit,
            schedule_fit=schedule_fit,
            required_upstream_dependencies_json=required_upstream_dependencies_json or {},
            required_subcontract_dependencies_json=required_subcontract_dependencies_json or {},
            risk_flags_json=risk_flags_json or {},
            missing_information_json=missing_information_json or {},
            confidence_score=confidence_score,
            explanation=explanation,
            created_at=now,
            updated_at=now,
        )
        self.db.add(result)
        self.db.flush()
        return result

    def create_capability_fit_report(
        self,
        project_id: str,
        actor_id: str,
        cad_cnc_match_id: str,
        buyer_facing_summary_en: Optional[str] = None,
        buyer_facing_summary_zh: Optional[str] = None,
        internal_summary: Optional[str] = None,
        can_quote_now: bool = False,
        can_make_in_house: bool = False,
        recommended_next_actions_json: Optional[dict] = None,
        required_upstream_inquiries_json: Optional[dict] = None,
        required_subcontractor_inquiries_json: Optional[dict] = None,
        risk_flags_json: Optional[dict] = None,
        confidence_score: float = 0.0,
        report_id: Optional[str] = None,
    ) -> CapabilityFitReport:
        now = _utcnow()
        report = CapabilityFitReport(
            report_id=report_id or new_uuid(),
            project_id=project_id,
            actor_id=actor_id,
            cad_cnc_match_id=cad_cnc_match_id,
            buyer_facing_summary_en=buyer_facing_summary_en,
            buyer_facing_summary_zh=buyer_facing_summary_zh,
            internal_summary=internal_summary,
            can_quote_now=can_quote_now,
            can_make_in_house=can_make_in_house,
            recommended_next_actions_json=recommended_next_actions_json or {},
            required_upstream_inquiries_json=required_upstream_inquiries_json or {},
            required_subcontractor_inquiries_json=required_subcontractor_inquiries_json or {},
            risk_flags_json=risk_flags_json or {},
            confidence_score=confidence_score,
            created_at=now,
            updated_at=now,
        )
        self.db.add(report)
        self.db.flush()
        return report
