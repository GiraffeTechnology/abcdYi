"""
B-side supplier response intake — appends supplier responses to a B-side workspace.
"""

from src.core_schema.b_side_types import BWWorkspace, SupplierResponseRecord
from src.b_side.workspace import get_b_workspace, save_b_workspace


def intake_supplier_response(b_workspace_id: str, response: SupplierResponseRecord) -> BWWorkspace:
    """
    Append a supplier response record to the B-side workspace.
    Replaces existing response for same supplier_id if present.
    """
    workspace = get_b_workspace(b_workspace_id)

    # Remove existing response from same supplier (dedup)
    workspace.supplier_responses = [
        r for r in workspace.supplier_responses if r.supplier_id != response.supplier_id
    ]
    workspace.supplier_responses.append(response)

    if workspace.status in ("created", "requirement_structured", "inquiry_drafted"):
        workspace.status = "collecting_responses"

    return save_b_workspace(workspace)
