"""
LLM distillation service — orchestrates the mandatory human-gated extraction pipeline.

Pipeline rules (per spec §4.4, enforced here before any DB write):
  1. Only Tier1 / Tier2 sources may enter this pipeline.
  2. LLM extraction_output is always created with status='pending'.
  3. Only a human reviewer can set status='approved'.
  4. Only approved records may be manually promoted to external_market_data.
  5. Rejected records are retained (never deleted) for error-pattern analysis.
"""
from __future__ import annotations


ALLOWED_SOURCE_TIERS = frozenset({"tier1", "tier2"})


class DistillationPipelineError(ValueError):
    """Raised when pipeline invariants would be violated."""


def validate_submission(source_tier: str, source_document_ref: str) -> None:
    """Gate check before creating a DistillationJob."""
    if source_tier not in ALLOWED_SOURCE_TIERS:
        raise DistillationPipelineError(
            f"来源等级 '{source_tier}' 不允许进入蒸馏流程。"
            f"仅接受 Tier1 / Tier2 已验证来源，Tier3 及无来源材料不可进入。"
        )
    if not source_document_ref or not source_document_ref.strip():
        raise DistillationPipelineError(
            "source_document_ref 不能为空，必须指向可验证的原始材料（如 PDF 路径、网页快照 URL 或海关数据文件引用）。"
        )


def validate_approval(extraction_output: dict | None, reviewed_by: str | None) -> None:
    """Gate check before marking a DistillationJob as approved."""
    if not extraction_output:
        raise DistillationPipelineError(
            "extraction_output 为空，无法标记为通过。请先完成 LLM 抽取步骤。"
        )
    if not reviewed_by or not reviewed_by.strip():
        raise DistillationPipelineError(
            "reviewed_by 不能为空，必须记录人工审核人身份后才能标记通过。"
        )


def build_extraction_prompt(source_document_text: str) -> str:
    """
    Returns a strictly constrained extraction prompt for the LLM call.
    The LLM acts as a structured parser only — estimation and inference are forbidden.
    """
    return (
        "你的任务是从以下原始材料中提取已存在的数字和字段，进行格式转换、单位换算、语言翻译和字段归类。\n"
        "\n"
        "严格禁止：\n"
        "  - 基于「行业常识」补全原始材料中没有的数字\n"
        "  - 在数字缺失时给出任何估算值\n"
        "  - 推断或假设任何未在原文中明确出现的数值\n"
        "\n"
        "规则：如原文中某字段缺失，对应输出字段必须设为 null，不得填写估算值或默认值。\n"
        "请以 JSON 格式输出提取结果，每个字段包含 value 和 source_text（原文片段）两个子字段。\n"
        "\n"
        "每个含交期的字段还需标注：\n"
        "  lead_time_relation: \"parallel\"（并联，可与同阶段其他项同步进行）或 \"sequential\"（串联，须等上一阶段完成）\n"
        "  lead_time_phase: 整数阶段号（行业默认：1=采购, 2=工艺, 3=生产, 4=包装）\n"
        "禁止估算——若无法从原文判断则填 null。\n"
        "\n"
        f"原始材料：\n{source_document_text}"
    )
