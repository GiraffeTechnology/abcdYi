"""
M-side inquiry receiver — creates or resumes a supplier workspace from a dispatched inquiry.
"""

from src.core_schema.m_side_types import MSideWorkspace, SupplierInquiryContext
from src.m_side.supplier_workspace import (
    create_m_workspace,
    get_m_workspace,
    find_workspace_by_invitation_token,
)
from src.m_side.supplier_profile import get_supplier_profile
from src.m_side.m_event_logger import log_m_event


def receive_supplier_inquiry(context: SupplierInquiryContext) -> MSideWorkspace:
    """
    Create or resume a supplier workspace from a dispatched inquiry.
    If workspace with same m_workspace_id already exists, return it.
    """
    # Check if workspace already exists
    try:
        existing = get_m_workspace(context.m_workspace_id)
        return existing
    except FileNotFoundError:
        pass

    # Load supplier profile
    profile = get_supplier_profile(context.supplier_id)
    if profile is None:
        # Create a minimal profile on the fly
        from src.m_side.supplier_profile import create_supplier_profile
        profile = create_supplier_profile(
            supplier_id=context.supplier_id,
            name=context.supplier_name,
        )

    workspace = create_m_workspace(context, profile)

    log_m_event(
        event_type="M_WORKSPACE_CREATED",
        m_workspace_id=workspace.m_workspace_id,
        b_workspace_id=workspace.b_workspace_id,
        supplier_id=workspace.supplier_id,
        rfq_id=workspace.rfq_id,
        payload={"inquiry_id": context.inquiry_id, "invitation_token": context.invitation_token},
    )

    return workspace


def format_inquiry_for_supplier(context: SupplierInquiryContext, language: str = "zh") -> str:
    """
    Format the inquiry message for display to a supplier through IM channels.
    """
    if language == "zh":
        lines = [
            "【Giraffe Agent 供应商询盘】",
            f"询盘编号：{context.rfq_id}",
            f"供应商工作区：{context.m_workspace_id}",
            f"验证码：{context.invitation_token}",
            "",
            "买方需求摘要：",
            context.inquiry_text_zh,
            "",
            "请回复以下信息：",
            "1. 是否可以生产 / 接单",
            "2. 可用产能与最早开工时间",
            "3. 物料是否可得",
            "4. 报价 / MOQ / 模具费 / 打样费",
            "5. 预计交期",
            "6. QC / 图片或视频更新能力",
            "7. 包装与物流安排",
            "8. 主要风险或限制",
            "",
            "你可以直接用自然语言回复。Giraffe Agent 会自动整理为结构化供应商响应。",
        ]
    else:
        lines = [
            "[Giraffe Agent Supplier Inquiry]",
            f"RFQ ID: {context.rfq_id}",
            f"Supplier Workspace: {context.m_workspace_id}",
            f"Token: {context.invitation_token}",
            "",
            "Buyer Requirement Summary:",
            context.inquiry_text_en,
            "",
            "Please reply with:",
            "1. Can you produce this item?",
            "2. Available capacity and earliest start date",
            "3. Is required material available?",
            "4. Unit price / MOQ / tooling fee / sample fee",
            "5. Estimated lead time",
            "6. QC / photo/video update capability",
            "7. Packaging and logistics terms",
            "8. Key risks or constraints",
            "",
            "You may reply in natural language. Giraffe Agent will structure your response.",
        ]
    return "\n".join(lines)
