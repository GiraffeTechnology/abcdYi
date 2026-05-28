"""
B-side supplier inquiry draft generator.
Generates bilingual (EN + ZH) supplier inquiry messages from structured BuyerRequirement.
"""

import uuid
from datetime import datetime, timezone

from src.core_schema.b_side_types import BuyerRequirement, SupplierInquiryDraft
from src.b_side.workspace import get_b_workspace


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


_REQUIRED_FIELDS = [
    "can_make",
    "lead_time_days",
    "unit_price",
    "currency",
    "material_available",
    "moq",
    "qc_available",
    "logistics_terms",
    "red_flags",
]


def _build_en_message(req: BuyerRequirement, rfq_id: str) -> str:
    lines = [
        f"[Giraffe Agent Supplier Inquiry]",
        f"RFQ ID: {rfq_id}",
        f"Category: {req.category or 'N/A'}",
        "",
        "Buyer Requirement Summary:",
        req.raw_text,
        "",
    ]
    if req.quantity:
        lines.append(f"Quantity: {req.quantity} pcs")
    if req.material:
        lines.append(f"Material: {req.material}")
    if req.specs_json:
        for k, v in req.specs_json.items():
            lines.append(f"{k.replace('_', ' ').title()}: {v}")
    if req.deadline:
        lines.append(f"Delivery Deadline: {req.deadline}")
    if req.destination:
        lines.append(f"Destination: {req.destination}")

    lines += [
        "",
        "Please reply with the following information:",
        "1. Can you produce this item? (Yes / No)",
        "2. Available capacity and earliest start date",
        "3. Is the required material available?",
        "4. Unit price / total price / MOQ / tooling fee / sample fee",
        "5. Estimated lead time (days)",
        "6. QC capability (photo/video updates available?)",
        "7. Packaging and logistics terms (EXW / FOB / DDP / courier)",
        "8. Key risks or constraints",
        "",
        "You may reply in natural language. Giraffe Agent will structure your response automatically.",
    ]
    return "\n".join(lines)


def _build_zh_message(req: BuyerRequirement, rfq_id: str) -> str:
    lines = [
        f"【Giraffe Agent 供应商询盘】",
        f"询盘编号：{rfq_id}",
        f"品类：{req.category or '未知'}",
        "",
        "买方需求摘要：",
        req.raw_text,
        "",
    ]
    if req.quantity:
        lines.append(f"数量：{req.quantity} 件")
    if req.material:
        lines.append(f"材料：{req.material}")
    if req.specs_json:
        for k, v in req.specs_json.items():
            lines.append(f"{k}：{v}")
    if req.deadline:
        lines.append(f"交货截止：{req.deadline}")
    if req.destination:
        lines.append(f"目的地：{req.destination}")

    lines += [
        "",
        "请回复以下信息：",
        "1. 是否可以生产 / 接单",
        "2. 可用产能与最早开工时间",
        "3. 物料是否可得",
        "4. 报价 / MOQ / 模具费 / 打样费",
        "5. 预计交期（天数）",
        "6. QC / 图片或视频更新能力",
        "7. 包装与物流安排（EXW / FOB / DDP / 快递）",
        "8. 主要风险或限制",
        "",
        "你可以直接用自然语言回复。Giraffe Agent 会自动整理为结构化供应商响应。",
    ]
    return "\n".join(lines)


def draft_supplier_inquiry(b_workspace_id: str, supplier_ids: list[str]) -> SupplierInquiryDraft:
    """
    Generate a bilingual supplier inquiry draft from a B-side workspace.
    """
    workspace = get_b_workspace(b_workspace_id)
    req = workspace.buyer_requirement

    if req is None:
        raise ValueError(f"Workspace {b_workspace_id} has no structured requirement yet.")

    inquiry_id = f"INQ-{uuid.uuid4().hex[:8].upper()}"

    msg_en = _build_en_message(req, req.rfq_id)
    msg_zh = _build_zh_message(req, req.rfq_id)

    draft = SupplierInquiryDraft(
        rfq_id=req.rfq_id,
        b_workspace_id=b_workspace_id,
        inquiry_id=inquiry_id,
        supplier_ids=supplier_ids,
        message_text_en=msg_en,
        message_text_zh=msg_zh,
        required_fields=_REQUIRED_FIELDS,
        created_at=_utcnow(),
    )
    return draft
