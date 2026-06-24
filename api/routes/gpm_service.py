from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from src.gpm.api.deps import get_quote_guidance_service
from src.gpm.api.schemas import ApprovalRequest, QuoteGuidanceRequest, RejectionRequest
from src.gpm.audit.gpm_audit_writer import GPMAuditWriter
from src.gpm.services.gpm_approval_service import GPMApprovalService
from src.gpm.services.gpm_quote_guidance_api_service import GPMQuoteGuidanceApiService

router = APIRouter()

_approval_svc = GPMApprovalService()
_audit_writer = GPMAuditWriter()


@router.get("/healthz")
def gpm_healthz() -> dict:
    return {
        "service": "gpm-quote-guidance",
        "status": "ok",
        "human_approval_required": True,
    }


@router.get("/capabilities")
def gpm_capabilities() -> dict:
    return {
        "service": "gpm-quote-guidance",
        "version": "F",
        "endpoints": [
            "GET /api/gpm/healthz",
            "GET /api/gpm/capabilities",
            "POST /api/gpm/quote-guidance",
            "GET /api/gpm/quote-guidance/{packet_id}",
            "POST /api/gpm/quote-guidance/{packet_id}/approve",
            "POST /api/gpm/quote-guidance/{packet_id}/reject",
        ],
        "constraints": {
            "human_approval_required": True,
            "no_automatic_business_actions": True,
            "private_first_llm_runtime": True,
            "audit_writeback": "best-effort",
        },
    }


@router.post("/quote-guidance", status_code=201)
def create_quote_guidance(
    req: QuoteGuidanceRequest,
    svc: Annotated[GPMQuoteGuidanceApiService, Depends(get_quote_guidance_service)],
) -> dict:
    result = svc.generate_quote_guidance(
        tenant_id=req.tenant_id,
        project_id=req.project_id,
        rfq_id=req.rfq_id,
        supplier_response_id=req.supplier_response_id,
        evidence_ids=req.evidence_ids,
        include_private_data=req.include_private_data,
        runtime_mode=req.runtime_mode,
    )

    if result["status"] == "runtime_unavailable":
        raise HTTPException(
            status_code=503,
            detail={
                "status": result["status"],
                "error": result["error"],
                "operator_action_required": result["operator_action_required"],
            },
        )
    if result["status"] == "insufficient_data":
        raise HTTPException(
            status_code=422,
            detail={"status": result["status"], "error": result["error"]},
        )
    if result["status"] == "context_unavailable":
        raise HTTPException(
            status_code=502,
            detail={
                "status": result["status"],
                "error": result["error"],
                "operator_action_required": result["operator_action_required"],
            },
        )

    packet = result["packet"]
    _audit_writer.write_execution_event({
        "event_type": "gpm_quote_guidance_created",
        "packet_id": packet.packet_id,
        "tenant_id": packet.tenant_id,
        "project_id": packet.project_id,
        "rfq_id": packet.rfq_id,
        "runtime_mode": packet.runtime_mode,
        "approval_status": packet.approval_status,
    })

    return {
        "status": "ok",
        "packet": packet.to_dict(),
        "human_approval_required": True,
        "operator_action_required": True,
    }


@router.get("/quote-guidance/{packet_id}")
def get_quote_guidance(
    packet_id: str,
    svc: Annotated[GPMQuoteGuidanceApiService, Depends(get_quote_guidance_service)],
) -> dict:
    packet = svc.get_packet(packet_id)
    if packet is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Packet {packet_id} not found"},
        )
    return {
        "status": "ok",
        "packet": packet.to_dict(),
        "human_approval_required": True,
    }


@router.post("/quote-guidance/{packet_id}/approve")
def approve_quote_guidance(
    packet_id: str,
    req: ApprovalRequest,
    svc: Annotated[GPMQuoteGuidanceApiService, Depends(get_quote_guidance_service)],
) -> dict:
    packet = svc.get_packet(packet_id)
    if packet is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Packet {packet_id} not found"},
        )
    if packet.approval_status != "pending":
        raise HTTPException(
            status_code=409,
            detail={
                "error": f"Packet {packet_id} is not pending (current: {packet.approval_status})"
            },
        )

    record = _approval_svc.record_approval(
        packet=packet,
        operator_id=req.operator_id,
        approval_note=req.approval_note,
        selected_option_id=req.selected_option_id,
    )

    _audit_writer.write_execution_event({
        "event_type": "gpm_quote_guidance_approved",
        "packet_id": packet_id,
        "operator_id": req.operator_id,
        "selected_option_id": req.selected_option_id,
    })

    return {
        "status": "ok",
        "approval_record": record.model_dump(),
        "dispatched": False,
        "dispatch_note": "No external action taken. Operator must act on the guidance manually.",
    }


@router.post("/quote-guidance/{packet_id}/reject")
def reject_quote_guidance(
    packet_id: str,
    req: RejectionRequest,
    svc: Annotated[GPMQuoteGuidanceApiService, Depends(get_quote_guidance_service)],
) -> dict:
    packet = svc.get_packet(packet_id)
    if packet is None:
        raise HTTPException(
            status_code=404,
            detail={"error": f"Packet {packet_id} not found"},
        )
    if packet.approval_status != "pending":
        raise HTTPException(
            status_code=409,
            detail={
                "error": f"Packet {packet_id} is not pending (current: {packet.approval_status})"
            },
        )

    record = _approval_svc.record_rejection(
        packet=packet,
        operator_id=req.operator_id,
        approval_note=req.approval_note,
    )

    _audit_writer.write_execution_event({
        "event_type": "gpm_quote_guidance_rejected",
        "packet_id": packet_id,
        "operator_id": req.operator_id,
    })

    return {
        "status": "ok",
        "approval_record": record.model_dump(),
        "dispatched": False,
        "dispatch_note": "No external action taken.",
    }
