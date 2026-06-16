"""
Role-Switching API — internal MVP endpoint that exercises the full M-side /
B-side upstream-sourcing pipeline end to end, over a real HTTP path.

Chain: resolve_role_context -> plan_upstream_dependencies ->
build_upstream_inquiry -> dispatch_upstream_inquiry -> parse_upstream_response
-> generate_upstream_options -> request_upstream_option_approval ->
approve_upstream_option -> generate_supplier_response_rollup ->
submit_rollup_to_b_side.

This is an internal MVP endpoint: it operates entirely on in-memory pydantic
models (no DB persistence) and is not tenant/user scoped.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.actors.role_resolver import resolve_role_context
from src.m_side.dependencies.dependency_planner import plan_upstream_dependencies
from src.m_side.upstream.inquiry_builder import build_upstream_inquiry
from src.m_side.upstream.dispatch_service import dispatch_upstream_inquiry
from src.m_side.upstream.response_parser import parse_upstream_response
from src.m_side.upstream.option_engine import generate_upstream_options
from src.m_side.upstream.approval_gate import (
    request_upstream_option_approval, approve_upstream_option,
)
from src.m_side.rollup.supplier_response_rollup import generate_supplier_response_rollup
from src.m_side.bridge.submit_rollup_to_b_side import submit_rollup_to_b_side

router = APIRouter(prefix="/api/role-switching", tags=["role-switching"])


class RunUpstreamPipelineRequest(BaseModel):
    project_id: str
    actor_id: str
    original_buyer_actor_id: str
    main_supplier_actor_id: str
    product_summary: str
    category: str
    quantity: int | None = None
    destination: str | None = None
    upstream_actor_id: str
    dependency_type: str | None = None
    raw_upstream_message: str
    approved_by: str
    b_workspace_id: str
    edge_id: str | None = None
    edge_type: str | None = None


class RunUpstreamPipelineResponse(BaseModel):
    role: str
    role_reason: str
    dependency_id: str
    dependency_type: str
    inquiry_id: str
    dispatch_status: str
    response_can_supply: bool
    option_count: int
    approved_option_id: str | None = None
    rollup_id: str | None = None
    can_accept_order: bool | None = None
    submit_status: str | None = None
    supplier_response_record_id: str | None = None


@router.post("/run-upstream-pipeline", response_model=RunUpstreamPipelineResponse)
def run_upstream_pipeline(body: RunUpstreamPipelineRequest) -> RunUpstreamPipelineResponse:
    role_context = resolve_role_context(
        project_id=body.project_id,
        actor_id=body.actor_id,
        original_buyer_actor_id=body.original_buyer_actor_id,
        main_supplier_actor_id=body.main_supplier_actor_id,
        edge_id=body.edge_id,
        edge_type=body.edge_type,
    )

    dependencies = plan_upstream_dependencies(
        project_id=body.project_id,
        product_summary=body.product_summary,
        category=body.category,
        quantity=body.quantity,
        main_supplier_actor_id=body.main_supplier_actor_id,
        destination=body.destination,
    )
    if not dependencies:
        raise HTTPException(status_code=422, detail="No upstream dependencies identified for this project.")

    dependency = next(
        (d for d in dependencies if d.dependency_type == body.dependency_type),
        dependencies[0],
    )

    inquiry = build_upstream_inquiry(
        dependency=dependency,
        upstream_actor_id=body.upstream_actor_id,
        main_supplier_actor_id=body.main_supplier_actor_id,
        quantity=body.quantity,
    )
    dispatch_result = dispatch_upstream_inquiry(inquiry, channel="mock")

    response = parse_upstream_response(
        raw_message=body.raw_upstream_message,
        inquiry_id=inquiry.inquiry_id,
        project_id=body.project_id,
        upstream_actor_id=body.upstream_actor_id,
        dependency_id=dependency.dependency_id,
        dependency_type=dependency.dependency_type,
    )

    options = generate_upstream_options(
        project_id=body.project_id,
        dependency_id=dependency.dependency_id,
        dependency_type=dependency.dependency_type,
        responses=[response],
        main_supplier_actor_id=body.main_supplier_actor_id,
    )

    if not options:
        return RunUpstreamPipelineResponse(
            role=role_context.role,
            role_reason=role_context.role_reason,
            dependency_id=dependency.dependency_id,
            dependency_type=dependency.dependency_type,
            inquiry_id=inquiry.inquiry_id,
            dispatch_status=dispatch_result.status,
            response_can_supply=response.can_supply,
            option_count=0,
        )

    approval_request = request_upstream_option_approval(
        project_id=body.project_id,
        dependency_id=dependency.dependency_id,
        dependency_type=dependency.dependency_type,
        options=options,
    )
    approval_result = approve_upstream_option(
        approval_request=approval_request,
        approved_option_id=options[0].option_id,
        approved_by=body.approved_by,
        mode="human",
    )

    rollup = generate_supplier_response_rollup(
        project_id=body.project_id,
        main_supplier_actor_id=body.main_supplier_actor_id,
        approval_results=[approval_result],
        product_summary=body.product_summary,
        quantity=body.quantity,
    )

    try:
        submit_result = submit_rollup_to_b_side(
            rollup=rollup,
            b_workspace_id=body.b_workspace_id,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RunUpstreamPipelineResponse(
        role=role_context.role,
        role_reason=role_context.role_reason,
        dependency_id=dependency.dependency_id,
        dependency_type=dependency.dependency_type,
        inquiry_id=inquiry.inquiry_id,
        dispatch_status=dispatch_result.status,
        response_can_supply=response.can_supply,
        option_count=len(options),
        approved_option_id=approval_result.approved_option_id,
        rollup_id=rollup.rollup_id,
        can_accept_order=rollup.can_accept_order,
        submit_status=submit_result.status,
        supplier_response_record_id=submit_result.supplier_response_record_id,
    )
