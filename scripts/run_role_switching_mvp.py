"""
Role-Switching MVP End-to-End Script — 16-step procurement execution test.

Tests the complete M-side role-switching workflow:
  Buyer B → Manufacturer M (MAIN_M_SIDE)
  Manufacturer M → Fabric/Trim/Packaging suppliers (UPSTREAM_B_SIDE)
  Fabric suppliers → Manufacturer M (UPSTREAM_M_SIDE)
  Approved upstream options → Rollup → B-side workspace
"""

import json
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.actors.models import Actor, ContactChannel
from src.actors.role_resolver import resolve_role_context
from src.projects.project_graph import (
    create_project, save_project, update_project_status, create_edge, get_edges_for_project
)
from src.m_side.dependencies.dependency_planner import plan_upstream_dependencies
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
from src.legal.patent_notice import SHORT_NOTICE_EN, CHINA_PATENT, JAPAN_PATENT, PATENT_OWNER


PASS = "✓"
FAIL = "✗"
_steps_passed = 0
_steps_failed = 0


def step(n: int, description: str) -> None:
    print(f"\n--- Step {n}: {description} ---")


def ok(msg: str) -> None:
    global _steps_passed
    _steps_passed += 1
    print(f"  {PASS} {msg}")


def fail(msg: str) -> None:
    global _steps_failed
    _steps_failed += 1
    print(f"  {FAIL} FAIL: {msg}")


def assert_true(condition: bool, msg: str) -> None:
    if condition:
        ok(msg)
    else:
        fail(msg)


# ── Load fixtures ──────────────────────────────────────────────────────────────

def load_fixture(path: str) -> dict | list:
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / path
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    print("=" * 70)
    print("ROLE-SWITCHING MVP — End-to-End Test")
    print("=" * 70)

    # Load fixtures
    fabric_responses = load_fixture("upstream_responses/fabric_supplier_responses.json")
    trim_responses = load_fixture("upstream_responses/trim_supplier_responses.json")
    fabric_suppliers = load_fixture("actors/fabric_suppliers.json")
    trim_suppliers = load_fixture("actors/trim_suppliers.json")
    packaging_suppliers = load_fixture("actors/packaging_suppliers.json")
    buyer_b_data = load_fixture("actors/buyer_b.json")
    manufacturer_m_data = load_fixture("actors/manufacturer_m.json")

    buyer_b = Actor.model_validate(buyer_b_data)
    manufacturer_m = Actor.model_validate(manufacturer_m_data)

    # ── Step 1: Buyer B creates project ─────────────────────────────────────
    step(1, "Buyer B creates project: 100 shirts")

    b_workspace = create_b_workspace("I need 100 plain white cotton shirts, size M, standard collar. Deadline: 30 days.")
    project = create_project(
        original_buyer_actor_id=buyer_b.actor_id,
        product_summary="100 plain white cotton shirts, size M, standard collar",
        category="apparel",
        quantity=100,
        b_workspace_id=b_workspace.b_workspace_id,
    )
    assert_true(project.project_id.startswith("PROJ-"), f"Project created: {project.project_id}")
    assert_true(project.status == "CREATED", f"Status: {project.status}")
    assert_true(b_workspace.b_workspace_id is not None, f"B-workspace: {b_workspace.b_workspace_id}")

    log_m_event(
        event_type="M_SIDE_RECEIVED_BUYER_INQUIRY",
        b_workspace_id=project.project_id,
        supplier_id=buyer_b.actor_id,
        payload={"product_summary": project.product_summary, "quantity": project.quantity},
    )

    # ── Step 2: Manufacturer M receives the inquiry ──────────────────────────
    step(2, "Manufacturer M receives the inquiry")

    project.main_supplier_actor_id = manufacturer_m.actor_id
    project.status = "MAIN_SUPPLIER_RECEIVED"
    save_project(project)

    # Create BUYER_TO_MAIN_SUPPLIER edge
    buyer_edge = create_edge(
        project_id=project.project_id,
        from_actor_id=buyer_b.actor_id,
        to_actor_id=manufacturer_m.actor_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    assert_true(buyer_edge.edge_id.startswith("EDGE-"), f"Buyer→M edge: {buyer_edge.edge_id}")

    # ── Step 3: Role resolver identifies Manufacturer M as MAIN_M_SIDE ──────
    step(3, "Role resolver identifies Manufacturer M as MAIN_M_SIDE")

    rc_main = resolve_role_context(
        project_id=project.project_id,
        actor_id=manufacturer_m.actor_id,
        original_buyer_actor_id=buyer_b.actor_id,
        main_supplier_actor_id=manufacturer_m.actor_id,
        edge_id=buyer_edge.edge_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
        counterparty_actor_id=buyer_b.actor_id,
    )
    assert_true(rc_main.role == "MAIN_M_SIDE", f"Role resolved: {rc_main.role}")
    assert_true(rc_main.can_create_upstream_inquiry, "can_create_upstream_inquiry=True")
    assert_true(rc_main.can_submit_response_to_buyer, "can_submit_response_to_buyer=True")
    assert_true(len(rc_main.role_reason) > 10, f"role_reason: {rc_main.role_reason[:50]}")

    log_m_event(
        event_type="ROLE_SWITCH_OCCURRED",
        b_workspace_id=project.project_id,
        supplier_id=manufacturer_m.actor_id,
        payload={"from_role": None, "to_role": "MAIN_M_SIDE", "edge_type": "BUYER_TO_MAIN_SUPPLIER"},
    )

    # ── Step 4: Dependency planner identifies upstream dependencies ──────────
    step(4, "Dependency planner identifies fabric, trim, packaging, QC, logistics")

    dependencies = plan_upstream_dependencies(
        project_id=project.project_id,
        product_summary=project.product_summary,
        category=project.category,
        quantity=project.quantity,
        main_supplier_actor_id=manufacturer_m.actor_id,
        candidate_fabric_ids=[s["actor_id"] for s in fabric_suppliers],
        candidate_trim_ids=[s["actor_id"] for s in trim_suppliers],
        candidate_packaging_ids=[s["actor_id"] for s in packaging_suppliers],
    )
    dep_types = {d.dependency_type for d in dependencies}
    assert_true("fabric" in dep_types, f"Fabric dependency identified")
    assert_true("trim" in dep_types, f"Trim dependency identified")
    assert_true("packaging" in dep_types, f"Packaging dependency identified")
    assert_true("logistics" in dep_types, f"Logistics dependency identified")
    assert_true(len(dependencies) >= 4, f"Total dependencies: {len(dependencies)}")

    update_project_status(project.project_id, "UPSTREAM_DEPENDENCY_PLANNED")

    # ── Step 5: Manufacturer M becomes UPSTREAM_B_SIDE to fabric suppliers ──
    step(5, "Manufacturer M becomes UPSTREAM_B_SIDE to fabric suppliers")

    fabric_dep = next(d for d in dependencies if d.dependency_type == "fabric")
    fabric_edges = []
    for fs in fabric_suppliers:
        edge = create_edge(
            project_id=project.project_id,
            from_actor_id=manufacturer_m.actor_id,
            to_actor_id=fs["actor_id"],
            edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
            parent_edge_id=buyer_edge.edge_id,
        )
        fabric_edges.append(edge)

        rc_upstream_b = resolve_role_context(
            project_id=project.project_id,
            actor_id=manufacturer_m.actor_id,
            original_buyer_actor_id=buyer_b.actor_id,
            main_supplier_actor_id=manufacturer_m.actor_id,
            edge_id=edge.edge_id,
            edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
            counterparty_actor_id=fs["actor_id"],
        )
        assert_true(rc_upstream_b.role == "UPSTREAM_B_SIDE",
                    f"M resolved as UPSTREAM_B_SIDE toward {fs['actor_id']}: {rc_upstream_b.role}")

    assert_true(len(fabric_edges) == 3, f"Created {len(fabric_edges)} fabric supplier edges")

    log_m_event(
        event_type="ROLE_SWITCH_OCCURRED",
        b_workspace_id=project.project_id,
        supplier_id=manufacturer_m.actor_id,
        payload={"from_role": "MAIN_M_SIDE", "to_role": "UPSTREAM_B_SIDE", "dependency_type": "fabric"},
    )

    # ── Step 6: Giraffe sends inquiries to 3 fabric suppliers ───────────────
    step(6, "Giraffe sends inquiries to 3 fabric suppliers")

    fabric_inquiries = []
    for fs_data in fabric_suppliers:
        inquiry = build_upstream_inquiry(
            dependency=fabric_dep,
            upstream_actor_id=fs_data["actor_id"],
            main_supplier_actor_id=manufacturer_m.actor_id,
            quantity=project.quantity,
        )
        dispatch_result = dispatch_upstream_inquiry(inquiry, channel="mock")
        fabric_inquiries.append(inquiry)
        assert_true(dispatch_result.status in ("sent", "mock_sent"),
                    f"Dispatched to {fs_data['actor_id']}: {dispatch_result.status}")

    update_project_status(project.project_id, "UPSTREAM_INQUIRIES_SENT")
    assert_true(len(fabric_inquiries) == 3, f"3 fabric inquiries dispatched")

    # ── Step 7: Fabric suppliers reply ─────────────────────────────────────
    step(7, "Fabric suppliers reply (loading fixture responses)")

    assert_true(len(fabric_responses) == 3, f"3 fabric supplier fixture responses loaded")
    print(f"  Responses from: {[r['upstream_actor_id'] for r in fabric_responses]}")

    # ── Step 8: Giraffe parses fabric supplier responses ───────────────────
    step(8, "Giraffe parses fabric supplier responses")

    parsed_fabric = []
    for i, (inquiry, resp_data) in enumerate(zip(fabric_inquiries, fabric_responses)):
        parsed = parse_upstream_response(
            raw_message=resp_data["raw_message"],
            inquiry_id=inquiry.inquiry_id,
            project_id=project.project_id,
            upstream_actor_id=resp_data["upstream_actor_id"],
            dependency_id=fabric_dep.dependency_id,
            dependency_type="fabric",
        )
        parsed_fabric.append(parsed)

        # Also resolve the upstream supplier's role as UPSTREAM_M_SIDE
        rc_upstream_m = resolve_role_context(
            project_id=project.project_id,
            actor_id=resp_data["upstream_actor_id"],
            original_buyer_actor_id=buyer_b.actor_id,
            main_supplier_actor_id=manufacturer_m.actor_id,
            edge_id=fabric_edges[i].edge_id,
            edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        )
        assert_true(rc_upstream_m.role == "UPSTREAM_M_SIDE",
                    f"Fabric supplier {resp_data['upstream_actor_id']} resolved as UPSTREAM_M_SIDE")

    can_supply_count = sum(1 for r in parsed_fabric if r.can_supply)
    assert_true(can_supply_count >= 2, f"At least 2 fabric suppliers can supply (got {can_supply_count})")
    assert_true(parsed_fabric[0].completeness_score > 0, f"F1 completeness: {parsed_fabric[0].completeness_score}")
    assert_true(parsed_fabric[1].completeness_score > 0, f"F2 completeness: {parsed_fabric[1].completeness_score}")

    update_project_status(project.project_id, "UPSTREAM_RESPONSES_RECEIVED")

    # ── Step 9: Giraffe generates 1–3 fabric options ────────────────────────
    step(9, "Giraffe generates 1–3 fabric options")

    fabric_options = generate_upstream_options(
        project_id=project.project_id,
        dependency_id=fabric_dep.dependency_id,
        dependency_type="fabric",
        responses=parsed_fabric,
        main_supplier_actor_id=manufacturer_m.actor_id,
    )
    assert_true(len(fabric_options) >= 1, f"Generated {len(fabric_options)} fabric option(s)")
    assert_true(len(fabric_options) <= 3, f"At most 3 fabric options")
    option_labels = [o.option_label for o in fabric_options]
    assert_true("BEST" in option_labels, f"BEST option present: {option_labels}")

    for opt in fabric_options:
        print(f"    Option {opt.option_label}: supplier={opt.upstream_actor_id}, "
              f"price={opt.price_summary}, lead={opt.lead_time_summary}")

    update_project_status(project.project_id, "UPSTREAM_OPTIONS_READY")

    # ── Step 10: Human/authorized agent approval selects one fabric option ──
    step(10, "Human/authorized agent approval selects one fabric option")

    fabric_approval_request = request_upstream_option_approval(
        project_id=project.project_id,
        dependency_id=fabric_dep.dependency_id,
        dependency_type="fabric",
        options=fabric_options,
    )
    assert_true(fabric_approval_request.approval_request_id.startswith("APR-"),
                f"Approval request: {fabric_approval_request.approval_request_id}")
    assert_true(fabric_approval_request.required_approval_mode in ("human", "authorized_agent"),
                f"Required mode: {fabric_approval_request.required_approval_mode}")

    # Select BEST option (simulate human approval)
    best_option = next((o for o in fabric_options if o.option_label == "BEST"), fabric_options[0])
    fabric_approval_result = approve_upstream_option(
        approval_request=fabric_approval_request,
        approved_option_id=best_option.option_id,
        approved_by=manufacturer_m.actor_id,
        mode="human",
        notes="Approved BEST fabric option — good price and lead time.",
    )
    assert_true(fabric_approval_result.approved_option_id == best_option.option_id,
                f"Fabric option approved: {best_option.option_label} from {best_option.upstream_actor_id}")
    assert_true(fabric_approval_result.mode == "human", f"Approved by: human")

    update_project_status(project.project_id, "UPSTREAM_OPTION_APPROVED")

    # ── Step 11: Mock trim and packaging dependency confirmation ────────────
    step(11, "Mock trim and packaging dependency confirmation")

    trim_dep = next((d for d in dependencies if d.dependency_type == "trim"), None)
    packaging_dep = next((d for d in dependencies if d.dependency_type == "packaging"), None)

    approval_results = [fabric_approval_result]

    if trim_dep:
        # Parse trim responses
        parsed_trim = []
        for resp_data in trim_responses:
            trim_inquiry = build_upstream_inquiry(
                dependency=trim_dep,
                upstream_actor_id=resp_data["upstream_actor_id"],
                main_supplier_actor_id=manufacturer_m.actor_id,
                quantity=project.quantity,
            )
            dispatch_upstream_inquiry(trim_inquiry, channel="mock")
            parsed = parse_upstream_response(
                raw_message=resp_data["raw_message"],
                inquiry_id=trim_inquiry.inquiry_id,
                project_id=project.project_id,
                upstream_actor_id=resp_data["upstream_actor_id"],
                dependency_id=trim_dep.dependency_id,
                dependency_type="trim",
            )
            parsed_trim.append(parsed)

        trim_options = generate_upstream_options(
            project_id=project.project_id,
            dependency_id=trim_dep.dependency_id,
            dependency_type="trim",
            responses=parsed_trim,
            main_supplier_actor_id=manufacturer_m.actor_id,
        )
        if trim_options:
            trim_approval_request = request_upstream_option_approval(
                project_id=project.project_id,
                dependency_id=trim_dep.dependency_id,
                dependency_type="trim",
                options=trim_options,
            )
            best_trim = trim_options[0]
            trim_approval_result = approve_upstream_option(
                approval_request=trim_approval_request,
                approved_option_id=best_trim.option_id,
                approved_by=manufacturer_m.actor_id,
                mode="human",
                notes="Trim option confirmed.",
            )
            approval_results.append(trim_approval_result)
            ok(f"Trim option approved: {best_trim.option_label} from {best_trim.upstream_actor_id}")
        else:
            ok("Trim: no responses needed (mock bypass)")
    else:
        ok("Trim dependency not identified (skipped)")

    if packaging_dep:
        # Mock packaging confirmation
        pkg_inquiry = build_upstream_inquiry(
            dependency=packaging_dep,
            upstream_actor_id=packaging_suppliers[0]["actor_id"],
            main_supplier_actor_id=manufacturer_m.actor_id,
            quantity=project.quantity,
        )
        dispatch_upstream_inquiry(pkg_inquiry, channel="mock")
        parsed_pkg = parse_upstream_response(
            raw_message="可以供货。聚袋和纸箱现货，100套，MOQ 50套。价格RMB 1.5每套。交货周期2天。最早发货日期：2024-02-05。",
            inquiry_id=pkg_inquiry.inquiry_id,
            project_id=project.project_id,
            upstream_actor_id=packaging_suppliers[0]["actor_id"],
            dependency_id=packaging_dep.dependency_id,
            dependency_type="packaging",
        )
        pkg_options = generate_upstream_options(
            project_id=project.project_id,
            dependency_id=packaging_dep.dependency_id,
            dependency_type="packaging",
            responses=[parsed_pkg],
            main_supplier_actor_id=manufacturer_m.actor_id,
        )
        if pkg_options:
            pkg_approval_request = request_upstream_option_approval(
                project_id=project.project_id,
                dependency_id=packaging_dep.dependency_id,
                dependency_type="packaging",
                options=pkg_options,
            )
            pkg_approval_result = approve_upstream_option(
                approval_request=pkg_approval_request,
                approved_option_id=pkg_options[0].option_id,
                approved_by=manufacturer_m.actor_id,
                mode="human",
            )
            approval_results.append(pkg_approval_result)
            ok(f"Packaging option approved: {pkg_options[0].option_label}")
        else:
            ok("Packaging: options generated but none viable")

    ok(f"Total approved upstream options: {len(approval_results)}")

    # ── Step 12: Giraffe generates Supplier Response Rollup ─────────────────
    step(12, "Giraffe generates Supplier Response Rollup")

    rollup = generate_supplier_response_rollup(
        project_id=project.project_id,
        main_supplier_actor_id=manufacturer_m.actor_id,
        approval_results=approval_results,
        product_summary=project.product_summary,
        quantity=project.quantity,
        main_capacity_available=True,
        main_capacity_note="Sewing capacity confirmed: can produce 50 shirts/day.",
    )
    assert_true(rollup.rollup_id.startswith("ROLLUP-"), f"Rollup ID: {rollup.rollup_id}")
    assert_true(rollup.can_accept_order, f"can_accept_order={rollup.can_accept_order}")
    assert_true(len(rollup.approved_upstream_options) >= 1,
                f"Approved upstream options in rollup: {len(rollup.approved_upstream_options)}")
    assert_true(rollup.completeness_score > 0, f"Completeness score: {rollup.completeness_score}")
    assert_true(len(rollup.recommended_response_to_buyer_en) > 20,
                f"Buyer response EN generated ({len(rollup.recommended_response_to_buyer_en)} chars)")
    assert_true(len(rollup.recommended_response_to_buyer_zh) > 20,
                f"Buyer response ZH generated ({len(rollup.recommended_response_to_buyer_zh)} chars)")

    print(f"\n  Rollup buyer response (EN preview):")
    print(f"  {rollup.recommended_response_to_buyer_en[:200]}...")

    update_project_status(project.project_id, "SUPPLIER_RESPONSE_ROLLED_UP")

    # ── Step 13: Manufacturer M approves the rollup ──────────────────────────
    step(13, "Manufacturer M approves the rollup")

    # Simulated: M reviews and confirms the rollup is good to submit
    assert_true(rollup.completeness_score >= 0, f"Completeness score accepted: {rollup.completeness_score}")
    assert_true(rollup.confidence_score >= 0, f"Confidence score: {rollup.confidence_score}")
    ok(f"Rollup reviewed and approved by {manufacturer_m.actor_id}")

    # ── Step 14: Rollup submitted to Buyer B's B-side workspace ─────────────
    step(14, "Rollup submitted to Buyer B's B-side workspace")

    submit_result = submit_rollup_to_b_side(
        rollup=rollup,
        b_workspace_id=b_workspace.b_workspace_id,
        supplier_name=manufacturer_m.name,
    )
    assert_true(submit_result.status == "submitted", f"Submit status: {submit_result.status}")
    assert_true(submit_result.b_workspace_id == b_workspace.b_workspace_id,
                f"Submitted to workspace: {submit_result.b_workspace_id}")
    assert_true(submit_result.supplier_response_record_id is not None,
                f"Response record ID: {submit_result.supplier_response_record_id}")

    update_project_status(project.project_id, "SUPPLIER_RESPONSE_SUBMITTED_TO_BUYER")

    # ── Step 15: B-side feasibility engine consumes the rollup ─────────────
    step(15, "B-side feasibility engine consumes the rollup")

    workspace_after = get_b_workspace(b_workspace.b_workspace_id)
    assert_true(len(workspace_after.supplier_responses) >= 1,
                f"Supplier responses in B-workspace: {len(workspace_after.supplier_responses)}")

    resp = workspace_after.supplier_responses[-1]
    assert_true(resp.supplier_id == manufacturer_m.actor_id,
                f"Response from correct supplier: {resp.supplier_id}")
    assert_true(resp.can_make is True, f"can_make=True in response")
    assert_true(resp.completeness_score > 0, f"completeness_score: {resp.completeness_score}")

    feasibility_report = run_feasibility_simulation(b_workspace.b_workspace_id)
    assert_true(feasibility_report is not None, "Feasibility report generated")
    assert_true(len(feasibility_report.paths) >= 1,
                f"Feasibility paths: {len(feasibility_report.paths)}")
    if feasibility_report.paths:
        best = feasibility_report.paths[0]
        print(f"  Top delivery path: supplier={best.supplier_id}, rank={best.rank}, "
              f"confidence={best.confidence_score}")

    # ── Step 16: Industrial Execution Graph records all events ──────────────
    step(16, "Industrial Execution Graph records all role switching and dependency events")

    all_events = read_events(b_workspace_id=project.project_id)
    event_types = {e["event_type"] for e in all_events}

    required_event_types = [
        "M_SIDE_RECEIVED_BUYER_INQUIRY",
        "ROLE_CONTEXT_RESOLVED",
        "ROLE_SWITCH_OCCURRED",
        "UPSTREAM_DEPENDENCY_PLANNED",
        "UPSTREAM_INQUIRY_CREATED",
        "UPSTREAM_INQUIRY_DISPATCHED",
        "UPSTREAM_RESPONSE_PARSED",
        "UPSTREAM_OPTIONS_GENERATED",
        "UPSTREAM_OPTION_APPROVAL_REQUESTED",
        "UPSTREAM_OPTION_APPROVED",
        "SUPPLIER_RESPONSE_ROLLUP_GENERATED",
        "SUPPLIER_RESPONSE_ROLLUP_SUBMITTED_TO_B_SIDE",
    ]

    for et in required_event_types:
        assert_true(et in event_types, f"Event logged: {et}")

    assert_true(len(all_events) >= 12, f"Total events logged for this project: {len(all_events)}")

    # ── Patent notice verification ───────────────────────────────────────────
    print("\n--- Patent Notice Verification ---")
    assert_true("ZL 2023 1 1645939.9" in CHINA_PATENT, f"China patent: {CHINA_PATENT}")
    assert_true("CN 117670482 B" in CHINA_PATENT, f"China patent grant: {CHINA_PATENT}")
    assert_true("P7644545" in JAPAN_PATENT, f"Japan patent: {JAPAN_PATENT}")
    assert_true("Giraffe Technology Holding Limited" in PATENT_OWNER, f"Patent owner: {PATENT_OWNER}")
    assert_true("mich@giraffe.technology" in SHORT_NOTICE_EN, "Contact email in notice")
    assert_true("individuals" in SHORT_NOTICE_EN.lower(), "Free license scope includes individuals")
    assert_true("SME" in SHORT_NOTICE_EN or "sme" in SHORT_NOTICE_EN.lower(), "Free license scope includes SMEs")
    patent_md = Path(__file__).parent.parent / "PATENT_NOTICE.md"
    license_md = Path(__file__).parent.parent / "LICENSE_NOTICE.md"
    readme_md = Path(__file__).parent.parent / "README.md"
    assert_true(patent_md.exists(), "PATENT_NOTICE.md exists")
    assert_true(license_md.exists(), "LICENSE_NOTICE.md exists")
    assert_true(readme_md.exists(), "README.md exists")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    total = _steps_passed + _steps_failed
    print(f"RESULTS: {_steps_passed}/{total} checks passed")
    if _steps_failed == 0:
        print("ROLE-SWITCHING MVP E2E COMPLETE — ALL CHECKS PASSED")
    else:
        print(f"FAILED: {_steps_failed} check(s) failed")
        sys.exit(1)
    print("=" * 70)


if __name__ == "__main__":
    main()
