"""
B+M End-to-End MVP Script — Giraffe Agent
Runs the complete B-side AI Buyer + M-side AI Merchandiser procurement execution loop.

Steps:
1. Create B-side workspace
2. Submit buyer requirement
3. Generate structured requirement
4. Generate supplier inquiry draft
5. Create 3 seed suppliers
6. Dispatch inquiry to 3 suppliers (creates 3 M-side workspaces)
7. Simulate 3 supplier replies through M-side workflow
8. Normalize each reply into SupplierResponsePacket
9. Push each supplier response to B-side workspace
10. Run B-side delivery feasibility simulation
11. Select best delivery path (rank 1)
12. Create M-side order execution workspace
13. Supplier acknowledges order
14. Supplier sends production update
15. Supplier sends QC update
16. Supplier sends logistics update
17. Print B+M execution summary
18. Print event log path
"""

import os
import sys

# Ensure project root is in path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from src.b_side.workspace import create_b_workspace, get_b_workspace, save_b_workspace
from src.b_side.requirement_structurer import structure_requirement
from src.b_side.inquiry_drafter import draft_supplier_inquiry
from src.b_side.feasibility_engine import run_feasibility_simulation
from src.b_side.event_logger import log_b_event

from src.m_side.seed_suppliers import seed_cnc_suppliers
from src.m_side.response_collector import append_supplier_message, build_response_packet_from_messages
from src.m_side.order_acknowledger import acknowledge_order
from src.m_side.production_update import submit_production_update
from src.m_side.qc_update import submit_qc_update
from src.m_side.logistics_update import submit_logistics_update
from src.m_side.m_event_logger import log_m_event, get_event_log_path, read_events

from src.bm_bridge.inquiry_dispatcher import dispatch_supplier_inquiry
from src.bm_bridge.response_bridge import push_supplier_response_to_b_side
from src.bm_bridge.order_bridge import create_order_execution_from_selected_path


def sep(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def step(n: int, desc: str) -> None:
    print(f"\n[Step {n:02d}] {desc}")
    print("-" * 50)


# ═══════════════════════════════════════════════════════
# STEP 1: Create B-side workspace
# ═══════════════════════════════════════════════════════
sep("Giraffe Agent B+M E2E MVP — Starting")

step(1, "Create B-side buyer workspace")
workspace = create_b_workspace("New workspace — will be updated with buyer requirement")
b_workspace_id = workspace.b_workspace_id
print(f"  B-workspace ID : {b_workspace_id}")
print(f"  RFQ ID (init)  : {workspace.rfq_id}")
print(f"  Status         : {workspace.status}")

log_b_event("B_WORKSPACE_CREATED", b_workspace_id, {"rfq_id": workspace.rfq_id})


# ═══════════════════════════════════════════════════════
# STEP 2: Submit buyer requirement
# ═══════════════════════════════════════════════════════
step(2, "Submit buyer requirement")
RAW_REQUIREMENT = (
    "Need 500 pcs aluminum 6061-T6 motor mount brackets, "
    "±0.02mm tolerance, black anodized, delivery Munich before July 10."
)
print(f"  Requirement: {RAW_REQUIREMENT}")

workspace.raw_requirement = RAW_REQUIREMENT
save_b_workspace(workspace)
log_b_event("B_REQUIREMENT_SUBMITTED", b_workspace_id, {"raw_text": RAW_REQUIREMENT})


# ═══════════════════════════════════════════════════════
# STEP 3: Generate structured requirement
# ═══════════════════════════════════════════════════════
step(3, "Generate structured requirement")
req = structure_requirement(b_workspace_id, RAW_REQUIREMENT)
workspace = get_b_workspace(b_workspace_id)
workspace.buyer_requirement = req
workspace.rfq_id = req.rfq_id  # sync RFQ id
workspace.status = "requirement_structured"
save_b_workspace(workspace)

print(f"  RFQ ID         : {req.rfq_id}")
print(f"  Category       : {req.category}")
print(f"  Quantity       : {req.quantity} pcs")
print(f"  Material       : {req.material}")
print(f"  Specs          : {req.specs_json}")
print(f"  Deadline       : {req.deadline}")
print(f"  Destination    : {req.destination}")
print(f"  Confidence     : {req.confidence_score:.0%}")
print(f"  Missing fields : {req.missing_fields}")

log_b_event("B_REQUIREMENT_STRUCTURED", b_workspace_id, {
    "rfq_id": req.rfq_id,
    "category": req.category,
    "confidence_score": req.confidence_score,
})


# ═══════════════════════════════════════════════════════
# STEP 4: Generate supplier inquiry draft
# ═══════════════════════════════════════════════════════
step(4, "Generate supplier inquiry draft")
# Placeholder supplier IDs — will be replaced after seeding
placeholder_ids = ["sup_cnc_strong_001", "sup_cnc_mid_002", "sup_cnc_cannot_003"]
draft = draft_supplier_inquiry(b_workspace_id, placeholder_ids)

workspace = get_b_workspace(b_workspace_id)
workspace.supplier_inquiry_draft = draft
workspace.status = "inquiry_drafted"
save_b_workspace(workspace)

print(f"  Inquiry ID     : {draft.inquiry_id}")
print(f"  Required fields: {draft.required_fields}")
print(f"  EN preview     : {draft.message_text_en[:120]}...")

log_b_event("B_INQUIRY_DRAFTED", b_workspace_id, {
    "inquiry_id": draft.inquiry_id,
    "supplier_count": len(placeholder_ids),
})


# ═══════════════════════════════════════════════════════
# STEP 5: Create 3 seed suppliers
# ═══════════════════════════════════════════════════════
step(5, "Create 3 seed CNC suppliers")
suppliers = seed_cnc_suppliers()
for s in suppliers:
    print(f"  Supplier: {s.supplier_name} [{s.supplier_id}] | Region: {s.region}")
supplier_ids = [s.supplier_id for s in suppliers]


# ═══════════════════════════════════════════════════════
# STEP 6: Dispatch inquiry to 3 suppliers
# ═══════════════════════════════════════════════════════
step(6, "Dispatch inquiry to 3 suppliers (creates 3 M-side workspaces)")
contexts = dispatch_supplier_inquiry(
    b_workspace_id=b_workspace_id,
    supplier_ids=supplier_ids,
    channel="mock",
)

print(f"\n  Dispatched to {len(contexts)} suppliers:")
for ctx in contexts:
    print(f"    ├ {ctx.supplier_name}")
    print(f"    │  M-workspace : {ctx.m_workspace_id}")
    print(f"    │  Token       : {ctx.invitation_token}")

m_workspace_ids = {ctx.supplier_id: ctx.m_workspace_id for ctx in contexts}


# ═══════════════════════════════════════════════════════
# STEP 7: Simulate 3 supplier replies through M-side workflow
# ═══════════════════════════════════════════════════════
step(7, "Simulate 3 supplier replies through M-side workflow")

SUPPLIER_REPLIES = {
    "sup_cnc_strong_001": (
        "可以做，6061材料有现货，最快下周一开工，样品7天，大货22天，"
        "单价USD 4.80，MOQ 500，阳极氧化外协需多3天，总交期25天。"
        "QC有，可提供照片。EXW工厂。"
    ),
    "sup_cnc_mid_002": (
        "可以接，材料在途，预计3天到，大货28天，单价USD 4.20，MOQ 300，"
        "阳极氧化需外协，多5天，总交期33天。QC有。FOB深圳。"
    ),
    "sup_cnc_cannot_003": (
        "抱歉，当前产能已满，无法接单。"
    ),
}

packets = {}
for supplier_id, reply in SUPPLIER_REPLIES.items():
    m_workspace_id = m_workspace_ids.get(supplier_id)
    if m_workspace_id is None:
        print(f"  WARNING: No workspace found for {supplier_id}")
        continue

    print(f"\n  Supplier {supplier_id}:")
    print(f"    Reply   : {reply[:80]}...")
    print(f"    Workspace: {m_workspace_id}")

    # Append the reply to M-side workspace
    append_supplier_message(m_workspace_id, reply)


# ═══════════════════════════════════════════════════════
# STEP 8: Normalize each reply into SupplierResponsePacket
# ═══════════════════════════════════════════════════════
step(8, "Normalize each reply into SupplierResponsePacket")

for supplier_id in supplier_ids:
    m_workspace_id = m_workspace_ids.get(supplier_id)
    if m_workspace_id is None:
        continue

    packet = build_response_packet_from_messages(m_workspace_id)
    packets[supplier_id] = packet

    can_make = packet.capacity_signal.can_make
    lead_time = packet.schedule_signal.estimated_lead_time_days
    price = packet.quote.unit_price
    currency = packet.quote.currency
    completeness = packet.completeness_score

    print(f"\n  {packet.supplier_name}:")
    print(f"    Can make       : {can_make}")
    print(f"    Lead time      : {lead_time} days")
    print(f"    Unit price     : {currency} {price}")
    print(f"    Red flags      : {packet.red_flags}")
    print(f"    Completeness   : {completeness:.0%}")
    print(f"    Confidence     : {packet.confidence_score:.0%}")
    print(f"    Summary        : {packet.supplier_summary_for_buyer}")


# ═══════════════════════════════════════════════════════
# STEP 9: Push each supplier response to B-side workspace
# ═══════════════════════════════════════════════════════
step(9, "Push each supplier response to B-side workspace")

for supplier_id, packet in packets.items():
    result = push_supplier_response_to_b_side(packet)
    print(f"  {packet.supplier_name}: pushed → can_make={result['can_make']}, "
          f"total_responses={result['total_responses']}")

log_m_event(
    event_type="M_RESPONSE_SUBMITTED_TO_B_SIDE",
    b_workspace_id=b_workspace_id,
    payload={"supplier_count": len(packets)},
)


# ═══════════════════════════════════════════════════════
# STEP 10: Run B-side feasibility simulation
# ═══════════════════════════════════════════════════════
step(10, "Run B-side delivery feasibility simulation")
report = run_feasibility_simulation(b_workspace_id)

print(f"\n  Feasibility Report for {report.rfq_id}:")
print(f"  Ranked paths ({len(report.paths)} eligible suppliers):")
for path in report.paths:
    print(f"    Rank {path.rank}: {path.supplier_name}")
    print(f"            Lead time    : {path.lead_time_days} days")
    print(f"            Unit price   : {path.currency} {path.unit_price}")
    print(f"            Confidence   : {path.confidence_score:.0%}")
    print(f"            Risk score   : {path.risk_score:.2f}")
    print(f"            Notes        : {path.notes}")

log_b_event("B_FEASIBILITY_SIMULATION_COMPLETE", b_workspace_id, {
    "eligible_suppliers": len(report.paths),
    "top_supplier": report.paths[0].supplier_name if report.paths else None,
})


# ═══════════════════════════════════════════════════════
# STEP 11: Select best delivery path (rank 1)
# ═══════════════════════════════════════════════════════
step(11, "Select best delivery path (Rank 1)")
if not report.paths:
    print("  ERROR: No eligible delivery paths found!")
    sys.exit(1)

best_path = report.paths[0]
selected_path_id = best_path.path_id
print(f"  Selected supplier   : {best_path.supplier_name}")
print(f"  Selected path ID    : {selected_path_id}")
print(f"  Lead time           : {best_path.lead_time_days} days")
print(f"  Unit price          : {best_path.currency} {best_path.unit_price}")

log_b_event("B_DELIVERY_PATH_SELECTED", b_workspace_id, {
    "selected_path_id": selected_path_id,
    "selected_supplier": best_path.supplier_name,
})


# ═══════════════════════════════════════════════════════
# STEP 12: Create M-side order execution workspace
# ═══════════════════════════════════════════════════════
step(12, "Create M-side order execution workspace")
order = create_order_execution_from_selected_path(b_workspace_id, selected_path_id)
order_execution_id = order.order_execution_id

print(f"  Order execution ID : {order_execution_id}")
print(f"  Supplier           : {best_path.supplier_name} [{order.supplier_id}]")
print(f"  Status             : {order.status}")
print(f"  Milestones         : {[m.name for m in order.milestones]}")


# ═══════════════════════════════════════════════════════
# STEP 13: Supplier acknowledges order
# ═══════════════════════════════════════════════════════
step(13, "Supplier acknowledges order")
ACK_MSG = "确认接单，按报价执行，预计6月20日完成。"
print(f"  Supplier message: {ACK_MSG}")

order = acknowledge_order(order_execution_id, ACK_MSG)
print(f"  Order status    : {order.status}")
ack_milestone = next((m for m in order.milestones if m.name == "order_acknowledgement"), None)
if ack_milestone:
    print(f"  ACK milestone   : {ack_milestone.status}")


# ═══════════════════════════════════════════════════════
# STEP 14: Supplier sends production update
# ═══════════════════════════════════════════════════════
step(14, "Supplier sends production update")
PROD_MSG = "材料已到，明天开机。生产进度40%。"
print(f"  Supplier message: {PROD_MSG}")

prod_update = submit_production_update(
    order_execution_id=order_execution_id,
    supplier_id=order.supplier_id,
    message=PROD_MSG,
)
print(f"  Update ID       : {prod_update.update_id}")
print(f"  Status          : {prod_update.status}")


# ═══════════════════════════════════════════════════════
# STEP 15: Supplier sends QC update
# ═══════════════════════════════════════════════════════
step(15, "Supplier sends QC update")
QC_MSG = "QC完成，尺寸合格，上传照片。"
QC_ATTACHMENTS = [{"type": "image", "ref": "mock://qc/bracket_qc_001.jpg"}]
print(f"  Supplier message: {QC_MSG}")
print(f"  Attachments     : {QC_ATTACHMENTS}")

qc_update = submit_qc_update(
    order_execution_id=order_execution_id,
    supplier_id=order.supplier_id,
    message=QC_MSG,
    attachments=QC_ATTACHMENTS,
)
print(f"  QC Update ID    : {qc_update.qc_update_id}")
print(f"  QC Status       : {qc_update.qc_status}")


# ═══════════════════════════════════════════════════════
# STEP 16: Supplier sends logistics update
# ═══════════════════════════════════════════════════════
step(16, "Supplier sends logistics update")
LOGISTICS_MSG = "已交付物流，快递单号：SF1234567890，预计6月28日到慕尼黑。"
print(f"  Supplier message: {LOGISTICS_MSG}")

lgs_update = submit_logistics_update(
    order_execution_id=order_execution_id,
    supplier_id=order.supplier_id,
    message=LOGISTICS_MSG,
)
print(f"  Logistics ID    : {lgs_update.logistics_update_id}")
print(f"  Status          : {lgs_update.status}")
print(f"  Tracking number : {lgs_update.tracking_number}")
print(f"  Carrier         : {lgs_update.carrier}")


# ═══════════════════════════════════════════════════════
# STEP 17: Print B+M execution summary
# ═══════════════════════════════════════════════════════
sep("B+M Execution Summary")

b_ws_final = get_b_workspace(b_workspace_id)
print(f"\n  B-side Workspace ID   : {b_workspace_id}")
print(f"  RFQ ID                : {b_ws_final.rfq_id}")
print(f"  B-side Status         : {b_ws_final.status}")
print(f"\n  Supplier Responses Received: {len(b_ws_final.supplier_responses)}")
for r in b_ws_final.supplier_responses:
    print(f"    ├ {r.supplier_name}: can_make={r.can_make} | "
          f"lead={r.estimated_lead_time_days}d | price={r.currency} {r.unit_price}")

if b_ws_final.feasibility_report:
    print(f"\n  Feasibility Report: {len(b_ws_final.feasibility_report.paths)} ranked paths")
    for path in b_ws_final.feasibility_report.paths:
        sel = " ← SELECTED" if path.path_id == selected_path_id else ""
        print(f"    Rank {path.rank}: {path.supplier_name} | "
              f"{path.lead_time_days}d | {path.currency} {path.unit_price}{sel}")

print(f"\n  Selected Supplier     : {best_path.supplier_name}")
print(f"  Selected Path ID      : {selected_path_id}")
print(f"  Order Execution ID    : {order_execution_id}")
print(f"  Order Status          : {order.status}")

print(f"\n  Post-confirmation updates:")
print(f"    Production update   : {prod_update.update_id} | {prod_update.status}")
print(f"    QC update           : {qc_update.qc_update_id} | {qc_update.qc_status}")
print(f"    Logistics update    : {lgs_update.logistics_update_id} | {lgs_update.status}")
if lgs_update.tracking_number:
    print(f"    Tracking number     : {lgs_update.tracking_number}")

# Event summary
all_events = read_events()
event_types = sorted({e["event_type"] for e in all_events})
print(f"\n  Total events logged   : {len(all_events)}")
print(f"  Event types logged    :")
for et in event_types:
    count = sum(1 for e in all_events if e["event_type"] == et)
    print(f"    [{count:2d}x] {et}")

# ═══════════════════════════════════════════════════════
# STEP 18: Print path to event log
# ═══════════════════════════════════════════════════════
step(18, "Event log path")
event_log_path = get_event_log_path()
print(f"\n  Industrial Execution Graph event log:")
print(f"  {event_log_path}")

sep("B+M E2E LOOP COMPLETE")
print()
print("  Giraffe Agent MVP B+M procurement execution loop completed successfully.")
print()
print("  Flow completed:")
print("  ✓ B-side buyer creates RFQ")
print("  ✓ B-side generates supplier inquiry")
print("  ✓ M-side dispatches inquiry to 3 suppliers")
print("  ✓ Suppliers reply through M-side workflow")
print("  ✓ M-side normalizes supplier responses")
print("  ✓ Responses returned to B-side")
print("  ✓ B-side ranks delivery paths")
print("  ✓ Buyer selects supplier (Rank 1)")
print("  ✓ M-side creates order execution workspace")
print("  ✓ Supplier acknowledges order")
print("  ✓ Supplier submits production / QC / logistics updates")
print("  ✓ Industrial Execution Graph events logged")
print()
