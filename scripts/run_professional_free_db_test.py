"""
Smoke Test 3: Professional Free CAD-CNC
1. Buyer B creates CNC project with CAD / STEP metadata.
2. Artifact record is created under Professional Free.
3. Warning event is recorded: Professional Free does not provide file encryption.
4. CADRequirementPacket is created.
5. ShopCapabilityProfile is loaded.
6. CADCNCMachiningMatchResult is created.
7. CapabilityFitReport is created.
8. Dependencies are created from match gaps.
9. SupplierResponseRollup includes CAD-to-CNC evidence.
10. ExecutionEvents exist for all steps.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.base import Base
from src.db.session import engine, SessionLocal
import src.db.models  # noqa: F401
from src.db.repositories.actor_repo import ActorRepo
from src.db.repositories.project_repo import ProjectRepo
from src.db.repositories.graph_repo import GraphRepo
from src.db.repositories.cad_cnc_repo import CADCNCRepo, PROFESSIONAL_FREE_WARNING
from src.db.repositories.rollup_repo import RollupRepo
from src.db.repositories.execution_event_repo import ExecutionEventRepo
from src.db.models.upstream import DependencyNeed
from src.db.mixins import new_uuid
from datetime import datetime, timezone


def utcnow():
    return datetime.now(timezone.utc)


def run():
    print("=" * 60)
    print("PROFESSIONAL FREE CAD-CNC DB TEST")
    print("=" * 60)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        actor_repo = ActorRepo(db)
        project_repo = ProjectRepo(db)
        graph_repo = GraphRepo(db)
        cad_repo = CADCNCRepo(db)
        rollup_repo = RollupRepo(db)
        event_repo = ExecutionEventRepo(db)

        # Setup actors
        buyer_b = actor_repo.create_actor(name="Buyer B (PF)", actor_type="buyer")
        manufacturer_m = actor_repo.create_actor(name="Manufacturer M (PF)", actor_type="manufacturer")
        heat_treat_supplier = actor_repo.create_actor(
            name="Heat Treatment Supplier HT1", actor_type="subcontractor"
        )
        surface_treat_supplier = actor_repo.create_actor(
            name="Surface Treatment ST1", actor_type="subcontractor"
        )

        # Step 1: Buyer B creates CNC project with CAD / STEP metadata
        print("\n[1] Buyer B creates CNC project with CAD/STEP metadata...")
        cnc_project = project_repo.create_project(
            original_buyer_actor_id=buyer_b.actor_id,
            main_supplier_actor_id=manufacturer_m.actor_id,
            category="cnc",
            product_summary="Precision aluminum bracket, 50pcs",
            quantity=50,
            status="CREATED",
            product_tier="professional_free",
            created_by_channel="web_fallback",
        )
        print(f"    OK: project_id={cnc_project.project_id}")

        buyer_supplier_edge = graph_repo.create_edge(
            project_id=cnc_project.project_id,
            from_actor_id=buyer_b.actor_id,
            to_actor_id=manufacturer_m.actor_id,
            edge_type="BUYER_TO_MAIN_SUPPLIER",
            status="SENT",
        )

        # Step 2: Artifact created under Professional Free (warning NOT yet acknowledged)
        print("\n[2] Creating artifact under Professional Free (no warning acknowledged)...")
        artifact_unacknowledged = cad_repo.create_artifact(
            file_ref="mock://cad/bracket_v1.step",
            artifact_type="step",
            project_id=cnc_project.project_id,
            owner_actor_id=buyer_b.actor_id,
            file_name="bracket_v1.step",
            mime_type="application/step",
            size_bytes=245760,
            product_tier="professional_free",
            warning_acknowledged=False,
        )
        assert artifact_unacknowledged.encryption_enabled == False
        assert artifact_unacknowledged.dynamic_watermark_enabled == False
        assert artifact_unacknowledged.secure_viewer_enabled == False
        print(f"    OK: artifact_id={artifact_unacknowledged.artifact_id}")
        print(f"    OK: encryption_enabled={artifact_unacknowledged.encryption_enabled} (Professional Free)")
        print(f"    OK: dynamic_watermark_enabled={artifact_unacknowledged.dynamic_watermark_enabled}")
        print(f"    OK: secure_viewer_enabled={artifact_unacknowledged.secure_viewer_enabled}")

        # Step 3: Warning event recorded
        print("\n[3] Recording Professional Free file warning event...")
        warn_event = event_repo.log_event(
            event_type="PROFESSIONAL_FREE_FILE_WARNING_SHOWN",
            project_id=cnc_project.project_id,
            actor_id=buyer_b.actor_id,
            payload_json={
                "warning": PROFESSIONAL_FREE_WARNING,
                "artifact_id": artifact_unacknowledged.artifact_id,
            },
            source_channel="mock",
        )
        print(f"    OK: warning_event_id={warn_event.event_id}")

        # Verify CADRequirementPacket creation fails without warning_acknowledged
        print("\n    Verifying CADRequirementPacket creation blocked without warning acknowledgement...")
        try:
            cad_repo.create_cad_requirement_packet(
                project_id=cnc_project.project_id,
                original_buyer_actor_id=buyer_b.actor_id,
                artifact_id=artifact_unacknowledged.artifact_id,
            )
            assert False, "Should have raised ValueError"
        except ValueError as ve:
            print(f"    OK: Correctly blocked: {str(ve)[:80]}...")

        # Acknowledge warning and create new artifact
        artifact_unacknowledged.warning_acknowledged = True
        db.flush()
        event_repo.log_event(
            event_type="PROFESSIONAL_FREE_CAP_LIMITATION_ACKNOWLEDGED",
            project_id=cnc_project.project_id,
            actor_id=buyer_b.actor_id,
            payload_json={"artifact_id": artifact_unacknowledged.artifact_id, "acknowledged": True},
            source_channel="mock",
        )
        print(f"    OK: Warning acknowledged for artifact {artifact_unacknowledged.artifact_id}")

        # Step 4: CADRequirementPacket created
        print("\n[4] Creating CADRequirementPacket...")
        packet = cad_repo.create_cad_requirement_packet(
            project_id=cnc_project.project_id,
            original_buyer_actor_id=buyer_b.actor_id,
            artifact_id=artifact_unacknowledged.artifact_id,
            main_supplier_actor_id=manufacturer_m.actor_id,
            part_summary="Aluminum 6061 bracket with M8 tapped holes, surface anodized",
            material="aluminum_6061",
            quantity=50,
            dimensions_json={"x_mm": 150, "y_mm": 80, "z_mm": 25},
            tolerance_requirements_json={"general": "0.05mm", "critical_bore": "0.02mm"},
            surface_finish_requirements_json={"ra_um": 1.6, "treatment": "anodized_type2"},
            thread_requirements_json={"M8_tapped": {"count": 4, "depth_mm": 15}},
            heat_treatment_requirements_json={"required": False},
            operation_requirements_json={"3_axis_milling": True, "drilling": True, "tapping": True},
            qc_requirements_json={"dimensional_inspection": True, "cmm_required": False},
            packaging_requirements_json={"individual_wrap": True},
            delivery_deadline="2026-07-01",
            extraction_confidence_score=0.88,
        )
        event_repo.log_event(
            event_type="CAD_REQUIREMENT_PACKET_CREATED",
            project_id=cnc_project.project_id,
            actor_id=buyer_b.actor_id,
            payload_json={"packet_id": packet.packet_id},
            source_channel="mock",
        )
        event_repo.log_event(
            event_type="CAD_FEATURES_EXTRACTED",
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"packet_id": packet.packet_id, "features": ["3_axis_milling", "tapping", "anodizing"]},
            source_channel="mock",
        )
        print(f"    OK: packet_id={packet.packet_id}")

        # Step 5: ShopCapabilityProfile loaded
        print("\n[5] Loading ShopCapabilityProfile...")
        shop_profile = cad_repo.create_shop_capability_profile(
            actor_id=manufacturer_m.actor_id,
            profile_name="M PF Shop Profile",
            machines_json={
                "cnc_3axis_haas": {
                    "name": "Haas VF-2 3-Axis", "axes": 3,
                    "work_envelope_mm": {"x": 508, "y": 406, "z": 508},
                },
            },
            qc_equipment_json={"caliper": True, "micrometer": True, "cmm": False},
            material_inventory_json={"aluminum_6061": True, "steel": True},
            in_house_processes_json={
                "3_axis_cnc_milling": True, "drilling": True, "tapping": True,
                "typical_tolerance_mm": 0.05, "best_tolerance_mm": 0.02,
            },
            outsourced_processes_json={"anodizing": True, "heat_treatment": True},
        )
        event_repo.log_event(
            event_type="SHOP_CAPABILITY_PROFILE_LOADED",
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"profile_id": shop_profile.profile_id},
            source_channel="mock",
        )
        print(f"    OK: shop_profile_id={shop_profile.profile_id}")

        # Step 6: CADCNCMachiningMatchResult created
        print("\n[6] Creating CADCNCMatchResult...")
        event_repo.log_event(
            event_type="CAD_CNC_MATCH_STARTED",
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"packet_id": packet.packet_id, "profile_id": shop_profile.profile_id},
            source_channel="mock",
        )
        match_result = cad_repo.create_match_result(
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            cad_requirement_packet_id=packet.packet_id,
            shop_capability_profile_id=shop_profile.profile_id,
            can_make_in_house=False,  # cannot do anodizing in-house
            recommended_machine_ids_json={"machines": ["cnc_3axis_haas"]},
            machine_fit_score=0.85,
            work_envelope_fit="fit",
            material_fit="fit",
            tolerance_fit="fit",
            surface_finish_fit="gap",  # anodizing not in-house
            tooling_fit="fit",
            qc_fit="fit",
            schedule_fit="limited",
            required_upstream_dependencies_json={},
            required_subcontract_dependencies_json={
                "anodizing": {"reason": "Surface anodizing not available in-house", "risk": "medium"}
            },
            risk_flags_json={"surface_finish": "anodizing must be outsourced"},
            confidence_score=0.85,
            explanation="3-axis CNC machining in-house is feasible. Anodizing must be subcontracted.",
        )
        event_repo.log_event(
            event_type="MACHINE_PARAMETER_MATCHED",
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"matched": ["work_envelope", "material", "tolerance", "tooling"]},
            source_channel="mock",
        )
        event_repo.log_event(
            event_type="MACHINE_PARAMETER_GAP_FOUND",
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"gap": "surface_finish", "reason": "anodizing not in-house"},
            source_channel="mock",
        )
        event_repo.log_event(
            event_type="CAD_CNC_MATCH_COMPLETED",
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"match_id": match_result.match_id, "can_make_in_house": False},
            source_channel="mock",
        )
        print(f"    OK: match_id={match_result.match_id}, can_make_in_house={match_result.can_make_in_house}")

        # Step 7: CapabilityFitReport created
        print("\n[7] Creating CapabilityFitReport...")
        fit_report = cad_repo.create_capability_fit_report(
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            cad_cnc_match_id=match_result.match_id,
            buyer_facing_summary_en=(
                "M can machine the aluminum bracket in-house using 3-axis CNC. "
                "Anodizing must be subcontracted. Lead time approx 14 days."
            ),
            buyer_facing_summary_zh="M可自行完成铝合金支架的3轴CNC加工，阳极氧化需外包，交货期约14天。",
            internal_summary="3-axis CNC fit confirmed. Anodizing subcontract dependency required.",
            can_quote_now=False,
            can_make_in_house=False,
            recommended_next_actions_json={
                "actions": ["inquire_anodizing_subcontractor", "confirm_schedule"]
            },
            required_upstream_inquiries_json={},
            required_subcontractor_inquiries_json={
                "anodizing": {"reason": "Type 2 anodizing required", "actor_type": "subcontractor"}
            },
            risk_flags_json={"anodizing": "must be outsourced"},
            confidence_score=0.85,
        )
        event_repo.log_event(
            event_type="CAPABILITY_FIT_REPORT_CREATED",
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={"report_id": fit_report.report_id},
            source_channel="mock",
        )
        print(f"    OK: report_id={fit_report.report_id}, can_make_in_house={fit_report.can_make_in_house}")

        # Step 8: Dependencies created from match gaps
        print("\n[8] Creating dependency from CAD-CNC match gap (anodizing)...")
        dep_anodizing = DependencyNeed(
            dependency_id=new_uuid(),
            project_id=cnc_project.project_id,
            created_by_actor_id=manufacturer_m.actor_id,
            dependency_type="surface_treatment",
            description="Type 2 anodizing for aluminum bracket",
            required_specs_json={"type": "anodized_type2", "thickness_um": 10},
            quantity_required=50.0,
            risk_level="medium",
            why_needed="Surface anodizing not available in-house per CAD-CNC gap analysis",
            candidate_actor_ids_json={"actors": [surface_treat_supplier.actor_id]},
            source="cad_cnc_match",
            status="pending",
            created_at=utcnow(), updated_at=utcnow(),
        )
        db.add(dep_anodizing)
        db.flush()
        event_repo.log_event(
            event_type="DEPENDENCY_CREATED_FROM_CAD_CNC_MATCH",
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={
                "dependency_id": dep_anodizing.dependency_id,
                "dependency_type": "surface_treatment",
                "source": "cad_cnc_match_gap",
            },
            source_channel="mock",
        )
        print(f"    OK: dep_anodizing={dep_anodizing.dependency_id} (surface_treatment)")

        # Step 9: SupplierResponseRollup includes CAD-to-CNC evidence
        print("\n[9] Creating SupplierResponseRollup with CAD-to-CNC evidence...")
        rollup = rollup_repo.create_rollup(
            project_id=cnc_project.project_id,
            main_supplier_actor_id=manufacturer_m.actor_id,
            can_accept_order=False,
            main_capacity_summary="M can machine in-house. Anodizing subcontract pending.",
            cad_requirement_packet_id=packet.packet_id,
            cad_cnc_match_id=match_result.match_id,
            capability_fit_report_id=fit_report.report_id,
            cnc_parameter_match_summary_json={
                "work_envelope": "fit", "material": "fit",
                "tolerance": "fit", "surface_finish": "gap",
            },
            can_make_in_house=False,
            recommended_machine_ids_json={"machines": ["cnc_3axis_haas"]},
            capability_gaps_json={"anodizing": "must be subcontracted"},
            upstream_dependency_basis_json={
                "anodizing": {"dependency_id": dep_anodizing.dependency_id, "status": "pending"}
            },
            unresolved_dependencies_json={"anodizing": dep_anodizing.dependency_id},
            risk_flags_json={"anodizing": "outsource required"},
            completeness_score=0.70,
            confidence_score=0.82,
            recommended_response_to_buyer_en=(
                "M can machine the bracket in-house. Anodizing subcontract inquiry in progress. "
                "Preliminary lead time 14 days pending anodizing confirmation."
            ),
        )
        event_repo.log_event(
            event_type="SUPPLIER_RESPONSE_ROLLUP_GENERATED",
            project_id=cnc_project.project_id,
            actor_id=manufacturer_m.actor_id,
            payload_json={
                "rollup_id": rollup.rollup_id,
                "includes_cad_cnc_evidence": True,
                "cad_cnc_match_id": match_result.match_id,
            },
            source_channel="mock",
        )
        print(f"    OK: rollup_id={rollup.rollup_id}")
        print(f"    OK: rollup.cad_cnc_match_id={rollup.cad_cnc_match_id}")
        print(f"    OK: rollup.capability_fit_report_id={rollup.capability_fit_report_id}")

        db.commit()

        # Step 10: Verify ExecutionEvents for all steps
        print("\n[10] Verifying ExecutionEvents for all steps...")
        events = event_repo.list_project_events(cnc_project.project_id)
        event_types_found = {e.event_type for e in events}
        required_events = {
            "PROFESSIONAL_FREE_FILE_WARNING_SHOWN",
            "PROFESSIONAL_FREE_CAP_LIMITATION_ACKNOWLEDGED",
            "CAD_REQUIREMENT_PACKET_CREATED",
            "CAD_FEATURES_EXTRACTED",
            "SHOP_CAPABILITY_PROFILE_LOADED",
            "CAD_CNC_MATCH_STARTED",
            "CAD_CNC_MATCH_COMPLETED",
            "MACHINE_PARAMETER_MATCHED",
            "MACHINE_PARAMETER_GAP_FOUND",
            "CAPABILITY_FIT_REPORT_CREATED",
            "DEPENDENCY_CREATED_FROM_CAD_CNC_MATCH",
            "SUPPLIER_RESPONSE_ROLLUP_GENERATED",
        }
        missing = required_events - event_types_found
        assert not missing, f"Missing events: {missing}"
        print(f"    OK: {len(events)} events found. All required types present.")

        # Verify Professional Free flags
        from src.db.models.artifact import Artifact
        reloaded_artifact = db.query(Artifact).filter(
            Artifact.artifact_id == artifact_unacknowledged.artifact_id
        ).first()
        assert reloaded_artifact.encryption_enabled == False
        assert reloaded_artifact.dynamic_watermark_enabled == False
        assert reloaded_artifact.secure_viewer_enabled == False
        print(f"    OK: Professional Free flags verified — no encryption/watermark/secure_viewer")

        print("\n" + "=" * 60)
        print("PROFESSIONAL FREE CAD-CNC TEST PASSED: All 10 steps completed.")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"\nPROFESSIONAL FREE TEST FAILED: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
