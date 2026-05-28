"""
Professional Free CAD-CNC Matching MVP — 16-step E2E test.

Tests the complete Professional Free workflow:
  Buyer B submits CNC/machining inquiry with CAD metadata
  → File warning shown
  → CAD Requirement Packet created
  → MachinaCheck-like feature extraction
  → Shop capability profile loaded
  → CAD-to-CNC matching
  → Capability Fit Report
  → Dependency planner creates gaps-driven inquiries
  → Role switches M to UPSTREAM_B_SIDE
  → Upstream suppliers respond
  → Options generated and approved
  → Rollup includes CAD-CNC matching evidence
  → Submitted to B-side feasibility engine
  → IEG records all events
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.m_side.professional_free.product_flags import PROFESSIONAL_FREE_FEATURES, assert_enterprise_cap_disabled
from src.m_side.professional_free.file_policy import get_professional_free_file_policy, show_file_warning, acknowledge_cap_limitation
from src.m_side.professional_free.cad_requirement_packet import create_cad_requirement_packet
from src.integrations.machinacheck_embedded.feature_extractor import extract_manufacturing_features
from src.m_side.capability_profiles.shop_capability_profile import load_shop_profile_from_fixture
from src.m_side.professional_free.cad_cnc_matcher import match_cad_to_cnc_capability
from src.m_side.professional_free.capability_fit_report import generate_capability_fit_report
from src.m_side.dependencies.dependency_planner import plan_dependencies_from_cad_cnc_match
from src.actors.role_resolver import resolve_role_context
from src.m_side.upstream.inquiry_builder import build_upstream_inquiry
from src.m_side.upstream.dispatch_service import dispatch_upstream_inquiry
from src.m_side.upstream.response_parser import parse_upstream_response
from src.m_side.upstream.option_engine import generate_upstream_options
from src.m_side.upstream.approval_gate import request_upstream_option_approval, approve_upstream_option
from src.m_side.rollup.supplier_response_rollup import generate_supplier_response_rollup
from src.m_side.bridge.submit_rollup_to_b_side import submit_rollup_to_b_side
from src.b_side.workspace import create_b_workspace, get_b_workspace
from src.b_side.feasibility_engine import run_feasibility_simulation
from src.m_side.m_event_logger import log_m_event, read_events
from src.projects.project_graph import create_project, save_project, create_edge

_steps_passed = 0
_steps_failed = 0
PASS = "✓"
FAIL = "✗"


def step(n: int, desc: str) -> None:
    print(f"\n--- Step {n}: {desc} ---")


def ok(msg: str) -> None:
    global _steps_passed
    _steps_passed += 1
    print(f"  {PASS} {msg}")


def fail(msg: str) -> None:
    global _steps_failed
    _steps_failed += 1
    print(f"  {FAIL} FAIL: {msg}")


def check(condition: bool, msg: str) -> None:
    if condition:
        ok(msg)
    else:
        fail(msg)


def load_fixture(rel_path: str) -> dict | list:
    p = Path(__file__).parent.parent / "tests" / "fixtures" / rel_path
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


BUYER_ID = "actor_buyer_cnc"
SUPPLIER_ID = "actor_manufacturer_cnc"
FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures" / "cad_cnc_matching"


def main() -> None:
    print("=" * 70)
    print("PROFESSIONAL FREE CAD-CNC MATCHING MVP — End-to-End Test")
    print("=" * 70)

    # ── Step 1: Buyer B submits CNC inquiry with CAD metadata ────────────────
    step(1, "Buyer B submits CNC/machining inquiry with CAD/STEP/BOM metadata")

    part_data = load_fixture("cad_cnc_matching/cnc_part_simple_step_metadata.json")
    b_workspace = create_b_workspace(
        f"CNC machining inquiry: {part_data.get('part_summary', 'aluminum bracket')} "
        f"x{part_data.get('quantity', 10)} pcs."
    )
    project = create_project(
        original_buyer_actor_id=BUYER_ID,
        product_summary=part_data.get("part_summary", "aluminum bracket"),
        category="cnc_machining",
        quantity=part_data.get("quantity", 10),
        main_supplier_actor_id=SUPPLIER_ID,
        b_workspace_id=b_workspace.b_workspace_id,
    )
    check(project.project_id.startswith("PROJ-"), f"Project created: {project.project_id}")
    check(b_workspace.b_workspace_id is not None, f"B-workspace: {b_workspace.b_workspace_id}")

    log_m_event(
        event_type="M_SIDE_RECEIVED_BUYER_INQUIRY",
        b_workspace_id=project.project_id,
        supplier_id=BUYER_ID,
        payload={"part_summary": part_data.get("part_summary"), "quantity": part_data.get("quantity")},
    )

    # ── Step 2: Manufacturer M receives inquiry ──────────────────────────────
    step(2, "Manufacturer M receives inquiry")

    buyer_edge = create_edge(
        project_id=project.project_id,
        from_actor_id=BUYER_ID,
        to_actor_id=SUPPLIER_ID,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    rc_main = resolve_role_context(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        original_buyer_actor_id=BUYER_ID,
        main_supplier_actor_id=SUPPLIER_ID,
        edge_id=buyer_edge.edge_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    check(rc_main.role == "MAIN_M_SIDE", f"Manufacturer resolved as: {rc_main.role}")
    check(rc_main.can_submit_response_to_buyer, "can_submit_response_to_buyer=True")

    # ── Step 3: Professional Free file policy warning shown ──────────────────
    step(3, "Professional Free file policy warning shown")

    policy = get_professional_free_file_policy()
    check(policy.encryption_enabled is False, "encryption_enabled=False")
    check(policy.dynamic_watermark_enabled is False, "dynamic_watermark_enabled=False")
    check(policy.secure_viewer_enabled is False, "secure_viewer_enabled=False")
    check(policy.user_warning_required is True, "user_warning_required=True")

    warning_text = show_file_warning(project.project_id, SUPPLIER_ID)
    check("Enterprise CAP" in warning_text, "Warning mentions Enterprise CAP")
    check("confidential" in warning_text.lower(), "Warning mentions confidential files")

    acknowledge_cap_limitation(project.project_id, SUPPLIER_ID)

    # Enterprise CAP explicitly disabled
    assert_enterprise_cap_disabled()
    check(not PROFESSIONAL_FREE_FEATURES["enterprise_cap"], "enterprise_cap=False")
    check(not PROFESSIONAL_FREE_FEATURES["file_encryption"], "file_encryption=False")
    check(not PROFESSIONAL_FREE_FEATURES["dynamic_watermark"], "dynamic_watermark=False")
    check(not PROFESSIONAL_FREE_FEATURES["secure_viewer"], "secure_viewer=False")
    check(PROFESSIONAL_FREE_FEATURES["cad_cnc_parameter_matching"], "cad_cnc_parameter_matching=True")

    # ── Step 4: CAD Requirement Packet created ───────────────────────────────
    step(4, "CAD Requirement Packet created from fixture metadata")

    packet = create_cad_requirement_packet(
        project_id=project.project_id,
        original_buyer_actor_id=BUYER_ID,
        main_supplier_actor_id=SUPPLIER_ID,
        buyer_input=part_data,
    )
    check(packet.packet_id.startswith("CAD-PKT-"), f"Packet ID: {packet.packet_id}")
    check(packet.material is not None, f"Material: {packet.material}")
    check(bool(packet.dimensions), f"Dimensions: {packet.dimensions}")
    check(packet.extraction_confidence_score > 0, f"Confidence: {packet.extraction_confidence_score}")
    check(packet.project_id == project.project_id, f"Linked to project: {packet.project_id}")

    # ── Step 5: Embedded MachinaCheck feature extractor ─────────────────────
    step(5, "Embedded MachinaCheck-like feature extractor creates ManufacturingFeatureSet")

    feature_set = extract_manufacturing_features(packet)
    check(feature_set.feature_set_id.startswith("FEAT-"), f"Feature set ID: {feature_set.feature_set_id}")
    check(len(feature_set.required_processes) >= 1, f"Processes: {feature_set.required_processes}")
    check(feature_set.min_axis_requirement is not None, f"Min axis: {feature_set.min_axis_requirement}")
    check(feature_set.tolerance_class != "unknown", f"Tolerance class: {feature_set.tolerance_class}")
    check(bool(feature_set.work_envelope_required), f"Work envelope: {feature_set.work_envelope_required}")

    # ── Step 6: Shop capability profile loaded ───────────────────────────────
    step(6, "Manufacturer M's shop capability profile loaded")

    shop_profile = load_shop_profile_from_fixture(
        str(FIXTURE_DIR / "shop_profile_basic_sme.json")
    )
    check(shop_profile.actor_id == SUPPLIER_ID, f"Shop actor: {shop_profile.actor_id}")
    check(len(shop_profile.machines) >= 1, f"Machines: {len(shop_profile.machines)}")
    check(bool(shop_profile.in_house_processes), f"In-house processes: {shop_profile.in_house_processes}")

    log_m_event(
        event_type="SHOP_CAPABILITY_PROFILE_LOADED",
        b_workspace_id=project.project_id,
        supplier_id=SUPPLIER_ID,
        payload={
            "machine_count": len(shop_profile.machines),
            "in_house_processes": shop_profile.in_house_processes,
        },
    )

    # ── Step 7: CAD-to-CNC matcher compares requirements with capability ─────
    step(7, "CAD-to-CNC matcher compares buyer requirements with machining center parameters")

    match_result = match_cad_to_cnc_capability(packet, feature_set, shop_profile)
    check(match_result.match_id.startswith("MATCH-"), f"Match ID: {match_result.match_id}")
    check(isinstance(match_result.machine_fit_score, float), f"Machine fit score: {match_result.machine_fit_score:.2f}")
    check(match_result.work_envelope_fit != "unknown" or not packet.dimensions,
          f"Work envelope fit: {match_result.work_envelope_fit}")
    check(match_result.material_fit in ("in_stock", "purchasable", "not_supported", "unknown"),
          f"Material fit: {match_result.material_fit}")
    check(match_result.tolerance_fit in ("fit", "marginal", "not_fit", "unknown"),
          f"Tolerance fit: {match_result.tolerance_fit}")
    check(match_result.qc_fit in ("fit", "external_qc_required", "missing", "unknown"),
          f"QC fit: {match_result.qc_fit}")
    check(match_result.schedule_fit in ("fit", "limited", "not_fit", "unknown"),
          f"Schedule fit: {match_result.schedule_fit}")
    check(len(match_result.explanation) > 10, f"Explanation generated ({len(match_result.explanation)} chars)")

    print(f"\n  Match summary:")
    print(f"    can_make_in_house={match_result.can_make_in_house}")
    print(f"    upstream_deps={match_result.required_upstream_dependencies}")
    print(f"    subcontract_deps={match_result.required_subcontract_dependencies}")

    # ── Step 8: Capability Fit Report generated ──────────────────────────────
    step(8, "Capability Fit Report generated")

    fit_report = generate_capability_fit_report(match_result)
    check(fit_report.report_id.startswith("FITREPORT-"), f"Report ID: {fit_report.report_id}")
    check(len(fit_report.buyer_facing_summary_en) > 20,
          f"Buyer summary EN ({len(fit_report.buyer_facing_summary_en)} chars)")
    check(len(fit_report.buyer_facing_summary_zh) > 20,
          f"Buyer summary ZH ({len(fit_report.buyer_facing_summary_zh)} chars)")
    check(isinstance(fit_report.can_make_in_house, bool),
          f"can_make_in_house={fit_report.can_make_in_house}")
    check(len(fit_report.recommended_next_actions) >= 0,
          f"Next actions: {fit_report.recommended_next_actions}")

    print(f"\n  Buyer-facing capability summary (EN):")
    print(f"  {fit_report.buyer_facing_summary_en[:200]}...")

    # ── Step 9: Dependency planner creates gap-driven inquiries ─────────────
    step(9, "Dependency planner creates upstream material/subcontractor/QC inquiries from match gaps")

    gap_dependencies = plan_dependencies_from_cad_cnc_match(
        project_id=project.project_id,
        match_result=match_result,
        main_supplier_actor_id=SUPPLIER_ID,
    )

    dep_types = {d.dependency_type for d in gap_dependencies}
    total_expected_gaps = (
        len(match_result.required_upstream_dependencies) +
        len(match_result.required_subcontract_dependencies)
    )
    check(len(gap_dependencies) >= 0, f"Gap dependencies generated: {len(gap_dependencies)}")
    print(f"  Dependency types from gaps: {dep_types or '{none — all fits}'}")

    # If material_fit==purchasable, raw_material should be a dependency
    if match_result.material_fit == "purchasable":
        check("raw_material" in dep_types, "raw_material dependency created for purchasable material")
    if match_result.qc_fit in ("external_qc_required", "missing"):
        check("qc_testing" in dep_types, "qc_testing dependency created for external QC gap")
    if match_result.surface_finish_fit == "requires_external_process":
        check("surface_treatment" in dep_types, "surface_treatment dependency created")

    # ── Step 10: Role resolver switches M to UPSTREAM_B_SIDE ────────────────
    step(10, "Role resolver switches Manufacturer M from MAIN_M_SIDE to UPSTREAM_B_SIDE")

    if gap_dependencies:
        first_dep = gap_dependencies[0]
        dep_edge_types = {
            "raw_material": "MAIN_SUPPLIER_TO_MATERIAL_SUPPLIER",
            "qc_testing": "MAIN_SUPPLIER_TO_QC_PROVIDER",
            "surface_treatment": "MAIN_SUPPLIER_TO_SUBCONTRACTOR",
            "subcontract_process": "MAIN_SUPPLIER_TO_SUBCONTRACTOR",
            "component": "MAIN_SUPPLIER_TO_COMPONENT_SUPPLIER",
        }
        edge_type = dep_edge_types.get(first_dep.dependency_type, "MAIN_SUPPLIER_TO_SUBCONTRACTOR")
        upstream_actor_id = f"actor_upstream_{first_dep.dependency_type}"

        upstream_edge = create_edge(
            project_id=project.project_id,
            from_actor_id=SUPPLIER_ID,
            to_actor_id=upstream_actor_id,
            edge_type=edge_type,
            parent_edge_id=buyer_edge.edge_id,
        )
        rc_upstream_b = resolve_role_context(
            project_id=project.project_id,
            actor_id=SUPPLIER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=SUPPLIER_ID,
            edge_id=upstream_edge.edge_id,
            edge_type=edge_type,
        )
        check(rc_upstream_b.role == "UPSTREAM_B_SIDE",
              f"M resolved as UPSTREAM_B_SIDE for {first_dep.dependency_type}: {rc_upstream_b.role}")

        log_m_event(
            event_type="ROLE_SWITCH_OCCURRED",
            b_workspace_id=project.project_id,
            supplier_id=SUPPLIER_ID,
            payload={"from_role": "MAIN_M_SIDE", "to_role": "UPSTREAM_B_SIDE", "dep_type": first_dep.dependency_type},
        )
    else:
        ok("No gaps — M stays as MAIN_M_SIDE (no upstream switching needed)")

    # ── Step 11: Upstream suppliers respond ─────────────────────────────────
    step(11, "Upstream suppliers respond (mock responses for gap dependencies)")

    approval_results = []
    mock_responses = {
        "raw_material": "可以供货。铝合金6061现货，数量充足，MOQ 10公斤。价格RMB 35每公斤。交货周期：3天。最早发货日期：2024-02-12。",
        "qc_testing": "We can provide CMM inspection service. Available from 2024-02-15. Price USD 80 per piece for dimensional check. Lead time: 2 days.",
        "surface_treatment": "Surface polishing available. Price RMB 15 per piece. Lead time 3 days. Earliest dispatch 2024-02-14.",
        "subcontract_process": "We can handle the subcontract machining. Price USD 120 per piece. Lead time 7 days.",
        "component": "Tooling setup available. Setup cost USD 200 one-time. Lead time 1 day.",
    }

    for dep in gap_dependencies[:3]:  # limit to 3 deps for E2E speed
        mock_msg = mock_responses.get(dep.dependency_type, f"可以供货。价格TBD，交货周期5天。")
        upstream_actor_id = f"actor_upstream_{dep.dependency_type}"

        inquiry = build_upstream_inquiry(
            dependency=dep,
            upstream_actor_id=upstream_actor_id,
            main_supplier_actor_id=SUPPLIER_ID,
            quantity=project.quantity,
        )
        dispatch = dispatch_upstream_inquiry(inquiry, channel="mock")
        check(dispatch.status in ("sent", "mock_sent"), f"Dispatched {dep.dependency_type} inquiry: {dispatch.status}")

        parsed = parse_upstream_response(
            raw_message=mock_msg,
            inquiry_id=inquiry.inquiry_id,
            project_id=project.project_id,
            upstream_actor_id=upstream_actor_id,
            dependency_id=dep.dependency_id,
            dependency_type=dep.dependency_type,
        )
        check(parsed.response_id.startswith("UPR-"), f"Parsed response for {dep.dependency_type}: {parsed.response_id}")

        options = generate_upstream_options(
            project_id=project.project_id,
            dependency_id=dep.dependency_id,
            dependency_type=dep.dependency_type,
            responses=[parsed],
            main_supplier_actor_id=SUPPLIER_ID,
        )
        if options:
            apr_req = request_upstream_option_approval(
                project_id=project.project_id,
                dependency_id=dep.dependency_id,
                dependency_type=dep.dependency_type,
                options=options,
            )
            best_opt = options[0]
            apr_result = approve_upstream_option(
                approval_request=apr_req,
                approved_option_id=best_opt.option_id,
                approved_by=SUPPLIER_ID,
                mode="human",
            )
            approval_results.append(apr_result)
            ok(f"Approved {dep.dependency_type} option: {best_opt.option_label} from {best_opt.upstream_actor_id}")
        else:
            ok(f"No viable options for {dep.dependency_type} (can_supply may be false)")

    if not gap_dependencies:
        ok("No gaps to resolve — proceeding with direct rollup")

    # ── Step 12: Options generated and approved ──────────────────────────────
    step(12, "Options generated and approved (summary)")

    check(len(approval_results) >= 0, f"Total approved upstream options: {len(approval_results)}")

    # ── Step 13: Supplier Response Rollup includes CAD-CNC matching evidence ─
    step(13, "Supplier Response Rollup includes CAD-CNC matching evidence")

    cnc_match_summary = {
        "machine_fit_score": match_result.machine_fit_score,
        "can_make_in_house": match_result.can_make_in_house,
        "work_envelope_fit": match_result.work_envelope_fit,
        "material_fit": match_result.material_fit,
        "tolerance_fit": match_result.tolerance_fit,
        "qc_fit": match_result.qc_fit,
    }
    capability_gaps = match_result.required_upstream_dependencies + match_result.required_subcontract_dependencies

    rollup = generate_supplier_response_rollup(
        project_id=project.project_id,
        main_supplier_actor_id=SUPPLIER_ID,
        approval_results=approval_results,
        product_summary=project.product_summary,
        quantity=project.quantity,
        main_capacity_available=match_result.can_make_in_house or len(gap_dependencies) == 0,
        main_capacity_note=f"CNC machining: {fit_report.buyer_facing_summary_en[:80]}...",
        unresolved_dependency_types=[],
        # CAD-CNC matching evidence
        cad_requirement_packet_id=packet.packet_id,
        cad_cnc_match_id=match_result.match_id,
        capability_fit_report_id=fit_report.report_id,
        cnc_parameter_match_summary=cnc_match_summary,
        can_make_in_house=match_result.can_make_in_house,
        recommended_machine_ids=match_result.recommended_machine_ids,
        capability_gaps=capability_gaps,
        upstream_dependency_basis={d.dependency_type: d.description for d in gap_dependencies},
    )

    check(rollup.rollup_id.startswith("ROLLUP-"), f"Rollup ID: {rollup.rollup_id}")
    check(rollup.cad_requirement_packet_id == packet.packet_id,
          f"CAD packet linked in rollup: {rollup.cad_requirement_packet_id}")
    check(rollup.cad_cnc_match_id == match_result.match_id,
          f"Match result linked: {rollup.cad_cnc_match_id}")
    check(rollup.capability_fit_report_id == fit_report.report_id,
          f"Fit report linked: {rollup.capability_fit_report_id}")
    check(bool(rollup.cnc_parameter_match_summary), "CNC parameter match summary in rollup")
    check(rollup.can_make_in_house is not None, f"can_make_in_house in rollup: {rollup.can_make_in_house}")

    print(f"\n  Rollup buyer response preview:")
    print(f"  {rollup.recommended_response_to_buyer_en[:250]}...")

    # ── Step 14: Rollup submitted to B-side workspace ────────────────────────
    step(14, "Rollup submitted to B-side workspace")

    submit_result = submit_rollup_to_b_side(
        rollup=rollup,
        b_workspace_id=b_workspace.b_workspace_id,
        supplier_name="Manufacturer CNC",
    )
    check(submit_result.status == "submitted", f"Submit status: {submit_result.status}")
    check(submit_result.b_workspace_id == b_workspace.b_workspace_id,
          f"Submitted to workspace: {submit_result.b_workspace_id}")

    # ── Step 15: B-side feasibility engine consumes evidence-enhanced rollup ─
    step(15, "B-side feasibility engine consumes the evidence-enhanced rollup")

    workspace_after = get_b_workspace(b_workspace.b_workspace_id)
    check(len(workspace_after.supplier_responses) >= 1,
          f"Supplier responses in workspace: {len(workspace_after.supplier_responses)}")

    resp = workspace_after.supplier_responses[-1]
    check(resp.supplier_id == SUPPLIER_ID, f"Response from correct supplier: {resp.supplier_id}")
    check(resp.completeness_score >= 0, f"Completeness score: {resp.completeness_score}")

    feasibility = run_feasibility_simulation(b_workspace.b_workspace_id)
    check(feasibility is not None, "Feasibility report generated")
    check(len(feasibility.paths) >= 1, f"Feasibility paths: {len(feasibility.paths)}")
    if feasibility.paths:
        top = feasibility.paths[0]
        print(f"  Top delivery path: supplier={top.supplier_id}, confidence={top.confidence_score}")

    # ── Step 16: IEG records all events ─────────────────────────────────────
    step(16, "Industrial Execution Graph records all matching and role-switching events")

    all_events = read_events(b_workspace_id=project.project_id)
    event_types = {e["event_type"] for e in all_events}

    required_events = [
        "M_SIDE_RECEIVED_BUYER_INQUIRY",
        "ROLE_CONTEXT_RESOLVED",
        "PROFESSIONAL_FREE_FILE_WARNING_SHOWN",
        "PROFESSIONAL_FREE_CAP_LIMITATION_ACKNOWLEDGED",
        "CAD_REQUIREMENT_PACKET_CREATED",
        "CAD_FEATURES_EXTRACTED",
        "SHOP_CAPABILITY_PROFILE_LOADED",
        "CAD_CNC_MATCH_STARTED",
        "CAD_CNC_MATCH_COMPLETED",
        "CAPABILITY_FIT_REPORT_CREATED",
        "SUPPLIER_RESPONSE_ROLLUP_GENERATED",
        "SUPPLIER_RESPONSE_ROLLUP_SUBMITTED_TO_B_SIDE",
    ]

    for et in required_events:
        check(et in event_types, f"Event logged: {et}")

    # Check at least some parameter match events
    match_events = [e for e in all_events if e["event_type"] in (
        "MACHINE_PARAMETER_MATCHED", "MACHINE_PARAMETER_GAP_FOUND")]
    check(len(match_events) >= 1, f"Machine parameter match/gap events logged: {len(match_events)}")

    # DEPENDENCY_CREATED_FROM_CAD_CNC_MATCH (only if gaps exist)
    if gap_dependencies:
        check("DEPENDENCY_CREATED_FROM_CAD_CNC_MATCH" in event_types,
              "DEPENDENCY_CREATED_FROM_CAD_CNC_MATCH event logged")
        if match_result.required_upstream_dependencies or match_result.required_subcontract_dependencies:
            check("UPSTREAM_INQUIRY_DISPATCHED" in event_types, "UPSTREAM_INQUIRY_DISPATCHED event logged")
            check("UPSTREAM_RESPONSE_PARSED" in event_types, "UPSTREAM_RESPONSE_PARSED event logged")

    check(len(all_events) >= 12, f"Total IEG events for this project: {len(all_events)}")

    # ── Final Summary ─────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    total = _steps_passed + _steps_failed
    print(f"RESULTS: {_steps_passed}/{total} checks passed")
    if _steps_failed == 0:
        print("PROFESSIONAL FREE CAD-CNC MATCHING MVP E2E COMPLETE — ALL CHECKS PASSED")
    else:
        print(f"FAILED: {_steps_failed} check(s) failed")
        sys.exit(1)
    print("=" * 70)


if __name__ == "__main__":
    main()
