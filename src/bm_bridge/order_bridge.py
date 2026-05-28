"""
B+M Bridge — Order Bridge.
Creates M-side order execution workspace after B-side buyer selects a delivery path.
"""

import uuid
from datetime import datetime, timezone

from src.core_schema.m_side_types import OrderExecutionContext, ProductionMilestone
from src.b_side.workspace import get_b_workspace, save_b_workspace
from src.m_side.order_acknowledger import save_order_execution
from src.m_side.supplier_workspace import get_m_workspace, update_m_workspace_status
from src.m_side.m_event_logger import log_m_event

_DEFAULT_MILESTONES = [
    "order_acknowledgement",
    "material_confirmation",
    "production_start",
    "mid_production_update",
    "qc_confirmation",
    "packaging_ready",
    "logistics_handover",
    "shipped",
    "completed",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_order_execution_from_selected_path(
    b_workspace_id: str,
    selected_path_id: str,
) -> OrderExecutionContext:
    """
    Create M-side order execution workspace after B-side buyer selects a supplier path.

    Looks up the selected delivery path in the feasibility report to find supplier and workspace.
    Creates default production milestones.
    """
    b_workspace = get_b_workspace(b_workspace_id)

    if b_workspace.feasibility_report is None:
        raise ValueError(f"No feasibility report in workspace {b_workspace_id}")

    # Find the selected path
    selected_path = None
    for path in b_workspace.feasibility_report.paths:
        if path.path_id == selected_path_id:
            selected_path = path
            break

    if selected_path is None:
        raise ValueError(f"Path {selected_path_id} not found in feasibility report")

    supplier_id = selected_path.supplier_id

    # Find M-side workspace for this supplier+b_workspace combo
    from src.m_side.supplier_workspace import list_m_workspaces
    m_workspace_id = None
    for ws in list_m_workspaces():
        if ws.b_workspace_id == b_workspace_id and ws.supplier_id == supplier_id:
            m_workspace_id = ws.m_workspace_id
            break

    if m_workspace_id is None:
        # Create a placeholder workspace ID
        m_workspace_id = f"mw_order_{uuid.uuid4().hex[:8]}"

    # Build milestones
    milestones = [
        ProductionMilestone(
            milestone_id=f"MS-{uuid.uuid4().hex[:6].upper()}",
            name=name,
            status="pending",
            evidence_required=(name in ("qc_confirmation", "shipped", "completed")),
        )
        for name in _DEFAULT_MILESTONES
    ]

    now = _utcnow()
    order = OrderExecutionContext(
        order_execution_id=f"OE-{uuid.uuid4().hex[:10].upper()}",
        b_workspace_id=b_workspace_id,
        m_workspace_id=m_workspace_id,
        supplier_id=supplier_id,
        selected_path_id=selected_path_id,
        status="order_acknowledgement_pending",
        milestones=milestones,
        created_at=now,
        updated_at=now,
    )

    # Persist to disk
    save_order_execution(order)

    # Update B-side workspace with selected path
    b_workspace.feasibility_report.selected_path_id = selected_path_id
    b_workspace.status = "supplier_selected"
    save_b_workspace(b_workspace)

    # Update M-side workspace status
    try:
        update_m_workspace_status(m_workspace_id, "selected_by_buyer")
    except FileNotFoundError:
        pass

    log_m_event(
        event_type="M_ORDER_EXECUTION_CREATED",
        m_workspace_id=m_workspace_id,
        b_workspace_id=b_workspace_id,
        supplier_id=supplier_id,
        rfq_id=b_workspace.rfq_id,
        order_execution_id=order.order_execution_id,
        payload={
            "selected_path_id": selected_path_id,
            "supplier_name": selected_path.supplier_name,
            "lead_time_days": selected_path.lead_time_days,
            "unit_price": selected_path.unit_price,
            "milestone_count": len(milestones),
        },
    )

    log_m_event(
        event_type="M_BUYER_SELECTED_SUPPLIER",
        m_workspace_id=m_workspace_id,
        b_workspace_id=b_workspace_id,
        supplier_id=supplier_id,
        rfq_id=b_workspace.rfq_id,
        payload={
            "selected_path_id": selected_path_id,
            "supplier_name": selected_path.supplier_name,
        },
    )

    return order
