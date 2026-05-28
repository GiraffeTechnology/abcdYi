"""
OpenClaw skill manifest for Giraffe Agent — B-side + M-side actions.
"""

SKILL_MANIFEST = {
    "name": "giraffe_agent",
    "version": "0.1.0",
    "description": "Giraffe Agent: AI Buyer (B-side) + AI Merchandiser / Supplier Response Agent (M-side)",
    "actions": [
        # B-side actions
        {
            "action": "b_side_create_workspace",
            "description": "Create a new B-side buyer workspace",
            "params": ["raw_requirement"],
        },
        {
            "action": "b_side_structure_requirement",
            "description": "Parse buyer requirement into structured format",
            "params": ["b_workspace_id"],
        },
        {
            "action": "b_side_draft_inquiry",
            "description": "Generate supplier inquiry draft",
            "params": ["b_workspace_id", "supplier_ids"],
        },
        {
            "action": "b_side_run_feasibility",
            "description": "Run delivery feasibility simulation",
            "params": ["b_workspace_id"],
        },
        {
            "action": "b_side_get_workspace",
            "description": "Get B-side workspace details",
            "params": ["b_workspace_id"],
        },
        # M-side actions
        {
            "action": "m_side_receive_inquiry",
            "description": "Receive a buyer inquiry on the supplier side",
            "params": ["m_workspace_id"],
        },
        {
            "action": "m_side_submit_supplier_response",
            "description": "Submit a natural-language supplier response for normalization",
            "params": ["m_workspace_id", "message"],
        },
        {
            "action": "m_side_get_pending_question",
            "description": "Get the next pending clarification question for supplier",
            "params": ["m_workspace_id"],
        },
        {
            "action": "m_side_submit_order_acknowledgement",
            "description": "Supplier acknowledges a confirmed order",
            "params": ["order_execution_id", "message"],
        },
        {
            "action": "m_side_submit_production_update",
            "description": "Supplier submits a production milestone update",
            "params": ["order_execution_id", "supplier_id", "message"],
        },
        {
            "action": "m_side_submit_qc_update",
            "description": "Supplier submits a QC update with optional attachments",
            "params": ["order_execution_id", "supplier_id", "message"],
        },
        {
            "action": "m_side_submit_logistics_update",
            "description": "Supplier submits a logistics / shipping update",
            "params": ["order_execution_id", "supplier_id", "message"],
        },
        {
            "action": "m_side_report_exception",
            "description": "Supplier reports an exception or risk",
            "params": ["m_workspace_id", "supplier_id", "message"],
        },
    ],
}
