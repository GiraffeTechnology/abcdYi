"""
M-side Send/Receive Role Switching Test — 15-step E2E verification.

Tests that Manufacturer M correctly switches between:
  MAIN_M_SIDE/INBOUND  (receiving buyer inquiry)
  UPSTREAM_B_SIDE/OUTBOUND  (sending upstream inquiries)
  UPSTREAM_B_SIDE/INBOUND  (receiving upstream replies)
  MAIN_M_SIDE/OUTBOUND  (sending rollup back to buyer)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.m_side.communication.role_switch_frame import create_role_switch_frame, get_frames_for_project
from src.m_side.communication.thread_context import create_thread, get_threads_for_project
from src.m_side.communication.correlation import generate_correlation_token, resolve_correlation_token
from src.m_side.communication.outbox_manager import create_outbound_message, approve_outbound_message, send_outbound_message
from src.m_side.communication.inbox_manager import receive_inbound_message
from src.m_side.communication.message_router import route_incoming_message
from src.m_side.communication.send_receive_state_machine import (
    create_send_receive_machine, transition_state,
)
from src.m_side.dependencies.dependency_planner import plan_upstream_dependencies
from src.m_side.upstream.inquiry_builder import build_upstream_inquiry
from src.m_side.upstream.dispatch_service import dispatch_upstream_inquiry
from src.m_side.upstream.response_parser import parse_upstream_response
from src.m_side.upstream.option_engine import generate_upstream_options
from src.m_side.upstream.approval_gate import request_upstream_option_approval, approve_upstream_option
from src.m_side.rollup.supplier_response_rollup import generate_supplier_response_rollup
from src.actors.role_resolver import resolve_role_context
from src.projects.project_graph import create_project, create_edge
from src.b_side.workspace import create_b_workspace
from src.m_side.m_event_logger import log_m_event, read_events

_steps_passed = 0
_steps_failed = 0


def step(n, desc):
    print(f"\n--- Step {n}: {desc} ---")


def ok(msg):
    global _steps_passed
    _steps_passed += 1
    print(f"  ✓ {msg}")


def fail(msg):
    global _steps_failed
    _steps_failed += 1
    print(f"  ✗ FAIL: {msg}")


def check(condition, msg):
    if condition:
        ok(msg)
    else:
        fail(msg)


BUYER_ID = "actor_buyer_sr_test"
SUPPLIER_ID = "actor_manufacturer_sr_test"
F1_ID = "actor_fabric_f1_sr"
F2_ID = "actor_fabric_f2_sr"
F3_ID = "actor_fabric_f3_sr"


def main():
    print("=" * 70)
    print("M-SIDE SEND/RECEIVE ROLE SWITCHING — End-to-End Test")
    print("=" * 70)

    # ── Step 1: Buyer B sends inquiry ─────────────────────────────────────────
    step(1, "Buyer B sends 100-shirt inquiry to Manufacturer M")

    b_workspace = create_b_workspace("Men's polo shirt, 100 pcs, cotton, white")
    project = create_project(
        original_buyer_actor_id=BUYER_ID,
        product_summary="Men's polo shirt 100pcs cotton",
        category="apparel",
        quantity=100,
        main_supplier_actor_id=SUPPLIER_ID,
        b_workspace_id=b_workspace.b_workspace_id,
    )
    check(project.project_id.startswith("PROJ-"), f"Project created: {project.project_id}")

    buyer_edge = create_edge(
        project_id=project.project_id,
        from_actor_id=BUYER_ID,
        to_actor_id=SUPPLIER_ID,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    check(buyer_edge.edge_id.startswith("EDGE-"), f"Buyer→M edge: {buyer_edge.edge_id}")

    # ── Step 2: M receives as MAIN_M_SIDE / INBOUND ───────────────────────────
    step(2, "M receives inquiry as MAIN_M_SIDE / INBOUND")

    rc_main = resolve_role_context(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        original_buyer_actor_id=BUYER_ID,
        main_supplier_actor_id=SUPPLIER_ID,
        edge_id=buyer_edge.edge_id,
        edge_type="BUYER_TO_MAIN_SUPPLIER",
    )
    check(rc_main.role == "MAIN_M_SIDE", f"M role: {rc_main.role}")

    buyer_thread = create_thread(
        project_id=project.project_id,
        edge_id=buyer_edge.edge_id,
        from_actor_id=BUYER_ID,
        to_actor_id=SUPPLIER_ID,
        thread_type="buyer_main_supplier",
        active_role_context_id="rc-main-buyer",
    )
    check(buyer_thread.thread_id.startswith("THREAD-"), f"Buyer-M thread: {buyer_thread.thread_id}")

    frame_inbound = create_role_switch_frame(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        role_context_id="rc-main-inbound",
        business_role="MAIN_M_SIDE",
        communication_direction="INBOUND",
        message_purpose="buyer_inquiry_received",
        counterparty_actor_id=BUYER_ID,
        edge_id=buyer_edge.edge_id,
        conversation_thread_id=buyer_thread.thread_id,
    )
    check(frame_inbound.frame_id.startswith("FRAME-"), f"Inbound frame: {frame_inbound.frame_id}")
    check(frame_inbound.communication_direction == "INBOUND", "Direction=INBOUND")
    check(frame_inbound.business_role == "MAIN_M_SIDE", "Role=MAIN_M_SIDE")

    routed = route_incoming_message(
        "Men's polo shirt 100 pcs, need quotation",
        {"project_id": project.project_id, "thread_type": "buyer_main_supplier",
         "actor_id": SUPPLIER_ID, "role_context_id": "rc-main"},
    )
    check(routed.business_role == "MAIN_M_SIDE", f"Routed role: {routed.business_role}")
    check(routed.communication_direction == "INBOUND", f"Routed direction: {routed.communication_direction}")
    check(routed.parser_target == "buyer_requirement_parser", f"Parser: {routed.parser_target}")

    inbound_msg = receive_inbound_message(
        "Men's polo shirt 100 pcs, need quotation",
        {"project_id": project.project_id, "edge_id": buyer_edge.edge_id,
         "from_actor_id": BUYER_ID, "to_actor_id": SUPPLIER_ID,
         "thread_id": buyer_thread.thread_id, "role_switch_frame_id": frame_inbound.frame_id},
        parsed_target="buyer_requirement_parser",
        parsed_result={"product": "polo shirt", "quantity": 100},
    )
    check(inbound_msg.inbound_message_id.startswith("IN-"), f"Inbound msg: {inbound_msg.inbound_message_id}")

    machine = create_send_receive_machine(project.project_id)
    machine = transition_state(project.project_id, "BUYER_INQUIRY_RECEIVED", "buyer inquiry received")
    check(machine.current_state == "BUYER_INQUIRY_RECEIVED", f"State: {machine.current_state}")

    # ── Step 3: M identifies fabric dependency ────────────────────────────────
    step(3, "M identifies fabric dependency and prepares upstream inquiries")

    deps = plan_upstream_dependencies(
        project_id=project.project_id,
        product_summary="Men's polo shirt 100pcs cotton",
        category="apparel",
        quantity=100,
        main_supplier_actor_id=SUPPLIER_ID,
        candidate_fabric_ids=[F1_ID, F2_ID, F3_ID],
    )
    fabric_deps = [d for d in deps if d.dependency_type == "fabric"]
    check(len(fabric_deps) >= 1, f"Fabric dependency planned: {len(fabric_deps)}")

    machine = transition_state(project.project_id, "PREPARING_UPSTREAM_INQUIRIES", "deps planned")
    check(machine.current_state == "PREPARING_UPSTREAM_INQUIRIES", f"State: {machine.current_state}")

    # ── Step 4: M approves sending upstream inquiries ─────────────────────────
    step(4, "M approves sending upstream inquiries")

    machine = transition_state(project.project_id, "AWAITING_MAIN_SUPPLIER_SEND_APPROVAL", "approval req")
    machine = transition_state(project.project_id, "SENDING_UPSTREAM_INQUIRIES", "M approved")
    check(machine.current_state == "SENDING_UPSTREAM_INQUIRIES", f"State: {machine.current_state}")

    # ── Step 5: M sends to F1/F2/F3 as UPSTREAM_B_SIDE / OUTBOUND ─────────────
    step(5, "M sends upstream inquiries as UPSTREAM_B_SIDE / OUTBOUND")

    fabric_dep = fabric_deps[0]
    upstream_frames = []
    outbound_msgs = []
    last_token = ""

    for supplier_id in [F1_ID, F2_ID, F3_ID]:
        upstream_edge = create_edge(
            project_id=project.project_id,
            from_actor_id=SUPPLIER_ID,
            to_actor_id=supplier_id,
            edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
            parent_edge_id=buyer_edge.edge_id,
        )
        rc_upstream = resolve_role_context(
            project_id=project.project_id,
            actor_id=SUPPLIER_ID,
            original_buyer_actor_id=BUYER_ID,
            main_supplier_actor_id=SUPPLIER_ID,
            edge_id=upstream_edge.edge_id,
            edge_type="MAIN_SUPPLIER_TO_FABRIC_SUPPLIER",
        )
        check(rc_upstream.role == "UPSTREAM_B_SIDE", f"M as UPSTREAM_B_SIDE for {supplier_id}")

        token = generate_correlation_token(
            project.project_id, upstream_edge.edge_id, fabric_dep.dependency_id
        )
        check(token.startswith("GFR-"), f"Correlation token for {supplier_id}: {token[:20]}...")
        last_token = token

        upstream_thread = create_thread(
            project_id=project.project_id,
            edge_id=upstream_edge.edge_id,
            from_actor_id=SUPPLIER_ID,
            to_actor_id=supplier_id,
            thread_type="main_supplier_upstream",
            active_role_context_id="rc-upstream",
            correlation_token=token,
        )

        inquiry = build_upstream_inquiry(
            dependency=fabric_dep,
            upstream_actor_id=supplier_id,
            main_supplier_actor_id=SUPPLIER_ID,
            quantity=project.quantity,
        )
        dispatch_upstream_inquiry(inquiry, channel="mock")

        frame_out = create_role_switch_frame(
            project_id=project.project_id,
            actor_id=SUPPLIER_ID,
            role_context_id="rc-upstream-out",
            business_role="UPSTREAM_B_SIDE",
            communication_direction="OUTBOUND",
            message_purpose="upstream_inquiry_to_supplier",
            counterparty_actor_id=supplier_id,
            edge_id=upstream_edge.edge_id,
            conversation_thread_id=upstream_thread.thread_id,
        )
        upstream_frames.append(frame_out)
        check(frame_out.business_role == "UPSTREAM_B_SIDE", f"OUTBOUND frame role for {supplier_id}")
        check(frame_out.communication_direction == "OUTBOUND", f"OUTBOUND frame direction")

        out_msg = create_outbound_message(
            project_id=project.project_id,
            from_actor_id=SUPPLIER_ID,
            to_actor_id=supplier_id,
            edge_id=upstream_edge.edge_id,
            role_context_id="rc-upstream-out",
            message_purpose="upstream_inquiry_to_supplier",
            body=inquiry.message_text_zh,
            thread_id=upstream_thread.thread_id,
        )
        outbound_msgs.append(out_msg)

    check(len(outbound_msgs) == 3, f"Outbound messages: {len(outbound_msgs)}")
    check(len(upstream_frames) == 3, f"Upstream OUTBOUND frames: {len(upstream_frames)}")
    machine = transition_state(project.project_id, "WAITING_FOR_UPSTREAM_RESPONSES", "inquiries sent")

    # ── Step 6: F1 replies ────────────────────────────────────────────────────
    step(6, "Fabric Supplier F1 replies")

    f1_reply = "可以供货，32支纯棉，价格 RMB 12.5/米，起订量 500 米，交期 15 天。" + last_token
    check(len(f1_reply) > 10, f"F1 reply message: {len(f1_reply)} chars")

    # ── Step 7: M receives reply as UPSTREAM_B_SIDE / INBOUND ─────────────────
    step(7, "M receives F1 reply as UPSTREAM_B_SIDE / INBOUND")

    frame_f1_in = create_role_switch_frame(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        role_context_id="rc-upstream-in",
        business_role="UPSTREAM_B_SIDE",
        communication_direction="INBOUND",
        message_purpose="upstream_response_received",
        counterparty_actor_id=F1_ID,
    )
    check(frame_f1_in.business_role == "UPSTREAM_B_SIDE", f"INBOUND frame role: {frame_f1_in.business_role}")
    check(frame_f1_in.communication_direction == "INBOUND", "INBOUND frame direction")

    # ── Step 8: Reply routed to upstream_response_parser ──────────────────────
    step(8, "Reply routed to upstream_response_parser")

    routed_f1 = route_incoming_message(
        f1_reply,
        {"project_id": project.project_id, "thread_type": "main_supplier_upstream",
         "actor_id": SUPPLIER_ID, "counterparty_actor_id": F1_ID},
    )
    check(routed_f1.parser_target == "upstream_response_parser",
          f"Parser target: {routed_f1.parser_target}")
    check(routed_f1.business_role == "UPSTREAM_B_SIDE", f"Business role: {routed_f1.business_role}")

    # ── Step 9: Correlation token links reply to fabric dependency ────────────
    step(9, "Correlation token links F1 reply to fabric dependency")

    correlation_result = resolve_correlation_token(
        f1_reply,
        {"project_id": project.project_id},
    )
    check(correlation_result.matched, f"Correlation token resolved: {correlation_result.matched}")
    check(correlation_result.confidence >= 0.9, f"Confidence: {correlation_result.confidence}")

    log_m_event(
        event_type="M_UPSTREAM_RESPONSE_ATTACHED_TO_DEPENDENCY",
        b_workspace_id=project.project_id,
        payload={
            "dependency_id": fabric_dep.dependency_id,
            "supplier_id": F1_ID,
            "token": correlation_result.raw_token,
        },
    )

    machine = transition_state(project.project_id, "UPSTREAM_RESPONSES_RECEIVED", "F1 replied")
    check(machine.current_state == "UPSTREAM_RESPONSES_RECEIVED", f"State: {machine.current_state}")

    # ── Step 10: M generates options and approves one ─────────────────────────
    step(10, "M generates options and approves one")

    parsed_f1 = parse_upstream_response(
        raw_message=f1_reply, inquiry_id="INQ-F1-SR", project_id=project.project_id,
        upstream_actor_id=F1_ID, dependency_id=fabric_dep.dependency_id, dependency_type="fabric",
    )
    f2_reply = "We can supply. USD 1.8/m, MOQ 300m, lead time 12 days."
    parsed_f2 = parse_upstream_response(
        raw_message=f2_reply, inquiry_id="INQ-F2-SR", project_id=project.project_id,
        upstream_actor_id=F2_ID, dependency_id=fabric_dep.dependency_id, dependency_type="fabric",
    )

    options = generate_upstream_options(
        project_id=project.project_id,
        dependency_id=fabric_dep.dependency_id,
        dependency_type="fabric",
        responses=[parsed_f1, parsed_f2],
        main_supplier_actor_id=SUPPLIER_ID,
    )
    check(len(options) >= 1, f"Options generated: {len(options)}")
    check(options[0].option_label in ("BEST", "FASTEST", "SAFEST", "LOWEST_COST", "BACKUP"),
          f"Best option label: {options[0].option_label}")

    machine = transition_state(project.project_id, "PREPARING_UPSTREAM_OPTIONS", "options generated")
    machine = transition_state(project.project_id, "AWAITING_OPTION_APPROVAL", "approval requested")

    approval_req = request_upstream_option_approval(
        project_id=project.project_id,
        dependency_id=fabric_dep.dependency_id,
        dependency_type="fabric",
        options=options,
    )
    best_opt = next((o for o in options if o.option_label == "BEST"), options[0])
    approved = approve_upstream_option(
        approval_request=approval_req,
        approved_option_id=best_opt.option_id,
        approved_by=SUPPLIER_ID,
        mode="human",
    )
    check(approved.approved_option_id == best_opt.option_id, f"Option approved: {approved.approved_option_id}")

    machine = transition_state(project.project_id, "GENERATING_BUYER_ROLLUP", "option approved")

    # ── Step 11: M generates buyer-facing rollup ──────────────────────────────
    step(11, "M generates buyer-facing Supplier Response Rollup")

    rollup = generate_supplier_response_rollup(
        project_id=project.project_id,
        main_supplier_actor_id=SUPPLIER_ID,
        approval_results=[approved],
        product_summary=project.product_summary,
        quantity=project.quantity,
        main_capacity_available=True,
        main_capacity_note="Factory capacity confirmed for 100 pcs.",
    )
    check(rollup.rollup_id.startswith("ROLLUP-"), f"Rollup ID: {rollup.rollup_id}")
    check(rollup.can_accept_order, "can_accept_order=True")
    check(len(rollup.recommended_response_to_buyer_en) > 20, "Buyer EN response generated")

    machine = transition_state(project.project_id, "AWAITING_ROLLUP_APPROVAL", "rollup generated")

    # ── Step 12: M sends rollup to Buyer B as MAIN_M_SIDE / OUTBOUND ──────────
    step(12, "M sends rollup to Buyer B as MAIN_M_SIDE / OUTBOUND")

    rollup_thread = create_thread(
        project_id=project.project_id,
        edge_id=buyer_edge.edge_id,
        from_actor_id=SUPPLIER_ID,
        to_actor_id=BUYER_ID,
        thread_type="buyer_rollup_review",
        active_role_context_id="rc-main-out",
    )

    frame_rollup_out = create_role_switch_frame(
        project_id=project.project_id,
        actor_id=SUPPLIER_ID,
        role_context_id="rc-main-out",
        business_role="MAIN_M_SIDE",
        communication_direction="OUTBOUND",
        message_purpose="supplier_response_rollup_to_buyer",
        counterparty_actor_id=BUYER_ID,
        edge_id=buyer_edge.edge_id,
        conversation_thread_id=rollup_thread.thread_id,
    )
    check(frame_rollup_out.business_role == "MAIN_M_SIDE", f"Rollup OUTBOUND role")
    check(frame_rollup_out.communication_direction == "OUTBOUND", "Rollup OUTBOUND direction")

    rollup_out_msg = create_outbound_message(
        project_id=project.project_id,
        from_actor_id=SUPPLIER_ID,
        to_actor_id=BUYER_ID,
        edge_id=buyer_edge.edge_id,
        role_context_id="rc-main-out",
        message_purpose="supplier_response_rollup_to_buyer",
        body=rollup.recommended_response_to_buyer_en,
        thread_id=rollup_thread.thread_id,
    )
    approve_outbound_message(rollup_out_msg.outbound_message_id)
    sent_msg = send_outbound_message(rollup_out_msg.outbound_message_id)
    check(sent_msg.status == "SENT", f"Rollup message status: {sent_msg.status}")

    log_m_event(
        event_type="M_OUTBOUND_BUYER_ROLLUP_SENT",
        b_workspace_id=project.project_id,
        payload={"rollup_id": rollup.rollup_id, "outbound_msg": rollup_out_msg.outbound_message_id},
    )

    machine = transition_state(project.project_id, "SENDING_ROLLUP_TO_BUYER", "rollup sent")
    check(machine.current_state == "SENDING_ROLLUP_TO_BUYER", f"State: {machine.current_state}")

    # ── Step 13: All messages have RoleSwitchFrame ────────────────────────────
    step(13, "All messages are attached to RoleSwitchFrames")

    all_frames = get_frames_for_project(project.project_id)
    check(len(all_frames) >= 6, f"Total RoleSwitchFrames: {len(all_frames)}")
    roles_seen = {f.business_role for f in all_frames}
    directions_seen = {f.communication_direction for f in all_frames}
    check("MAIN_M_SIDE" in roles_seen, "MAIN_M_SIDE role in frames")
    check("UPSTREAM_B_SIDE" in roles_seen, "UPSTREAM_B_SIDE role in frames")
    check("INBOUND" in directions_seen, "INBOUND direction in frames")
    check("OUTBOUND" in directions_seen, "OUTBOUND direction in frames")

    # Verify buyer-facing and upstream messages are not mixed
    buyer_outbound = [f for f in all_frames
                      if f.business_role == "MAIN_M_SIDE" and f.communication_direction == "OUTBOUND"]
    upstream_outbound = [f for f in all_frames
                         if f.business_role == "UPSTREAM_B_SIDE" and f.communication_direction == "OUTBOUND"]
    check(len(buyer_outbound) >= 1, f"MAIN_M_SIDE/OUTBOUND frames: {len(buyer_outbound)}")
    check(len(upstream_outbound) >= 3, f"UPSTREAM_B_SIDE/OUTBOUND frames: {len(upstream_outbound)}")

    # Internal approval frames must not be sent to buyer
    internal_frames = [f for f in all_frames if f.communication_direction == "INTERNAL"]
    for f in internal_frames:
        check(f.counterparty_actor_id != BUYER_ID,
              f"Internal frame {f.frame_id} not directed to buyer")

    # ── Step 14: Messages attached to correct threads and edges ───────────────
    step(14, "Messages attached to correct threads and edges")

    all_threads = get_threads_for_project(project.project_id)
    thread_types = {t.thread_type for t in all_threads}
    check(len(all_threads) >= 4, f"Threads: {len(all_threads)}")
    check("buyer_main_supplier" in thread_types, "buyer_main_supplier thread")
    check("main_supplier_upstream" in thread_types, "main_supplier_upstream thread")
    check("buyer_rollup_review" in thread_types, "buyer_rollup_review thread")

    # ── Step 15: Execution events logged ─────────────────────────────────────
    step(15, "Execution events logged to Industrial Execution Graph")

    state_events = read_events(event_type="M_ROLE_SEND_RECEIVE_STATE_CHANGED", b_workspace_id=project.project_id)
    check(len(state_events) >= 5, f"State change events: {len(state_events)}")

    frame_events = read_events(event_type="M_ROLE_SWITCH_FRAME_CREATED", b_workspace_id=project.project_id)
    check(len(frame_events) >= 6, f"Frame creation events: {len(frame_events)}")

    outbound_events = read_events(event_type="M_OUTBOUND_UPSTREAM_INQUIRY_CREATED", b_workspace_id=project.project_id)
    check(len(outbound_events) >= 3, f"Outbound inquiry events: {len(outbound_events)}")

    corr_events = read_events(event_type="MESSAGE_CORRELATION_TOKEN_CREATED", b_workspace_id=project.project_id)
    check(len(corr_events) >= 3, f"Correlation token events: {len(corr_events)}")

    resolved_events = read_events(event_type="MESSAGE_CORRELATION_TOKEN_RESOLVED", b_workspace_id=project.project_id)
    check(len(resolved_events) >= 1, f"Correlation resolved events: {len(resolved_events)}")

    rollup_sent_events = read_events(event_type="M_OUTBOUND_BUYER_ROLLUP_SENT", b_workspace_id=project.project_id)
    check(len(rollup_sent_events) >= 1, f"Rollup sent events: {len(rollup_sent_events)}")

    # ── Final Report ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print(f"M-SIDE SEND/RECEIVE TEST: {_steps_passed} passed, {_steps_failed} failed")
    print(f"{'=' * 70}")
    if _steps_failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
