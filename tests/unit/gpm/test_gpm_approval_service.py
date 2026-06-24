from src.gpm.models.gpm_quote_guidance_packet import GPMQuoteGuidancePacket
from src.gpm.services.gpm_approval_service import GPMApprovalService


def _packet() -> GPMQuoteGuidancePacket:
    return GPMQuoteGuidancePacket.create(
        supplier_quote_position="above_benchmark",
        recommendation="negotiate",
        benchmark_range={},
        negotiation_points=[],
        buyer_quote_options=[],
        runtime_profile="ci",
        runtime_mode="mock",
        context_retriever="mock",
        data_mode="public",
    )


def test_record_approval_sets_status():
    svc = GPMApprovalService()
    p = _packet()
    rec = svc.record_approval(packet=p, operator_id="op1", approval_note="ok")
    assert p.approval_status == "approved"
    assert rec.approval_status == "approved"
    assert rec.dispatched is False
    assert "No external action" in rec.dispatch_note


def test_record_rejection_sets_status():
    svc = GPMApprovalService()
    p = _packet()
    rec = svc.record_rejection(packet=p, operator_id="op1", approval_note="too expensive")
    assert p.approval_status == "rejected"
    assert rec.approval_status == "rejected"
    assert rec.dispatched is False


def test_approval_record_carries_operator_id():
    svc = GPMApprovalService()
    p = _packet()
    rec = svc.record_approval(packet=p, operator_id="op-abc")
    assert rec.operator_id == "op-abc"
    assert rec.packet_id == p.packet_id


def test_approval_with_selected_option():
    svc = GPMApprovalService()
    p = _packet()
    rec = svc.record_approval(packet=p, operator_id="op1", selected_option_id="opt_accept")
    assert rec.selected_option_id == "opt_accept"
