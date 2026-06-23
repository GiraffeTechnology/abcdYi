from __future__ import annotations

import json

from src.gpm.context.gpm_context_bundle import GPMContextBundle


def build_qwen_semantic_analysis_prompt(context: GPMContextBundle) -> str:
    """Build a strict semantic analysis prompt for a local Qwen runtime.

    Enforces: JSON-only output, no invented prices/MOQ/supplier IDs,
    evidence citation only, no buyer quote dispatch.
    """
    payload = context.to_prompt_payload()

    return (
        "You are a pricing intelligence assistant for GPM (Giraffe Pricing Model).\n"
        "\n"
        "STRICT RULES:\n"
        "- Return JSON only. No free text, no markdown, no explanation outside JSON.\n"
        "- Do not invent prices not present in the evidence.\n"
        "- Do not invent MOQ values not present in the evidence.\n"
        "- Do not invent supplier IDs not present in the evidence.\n"
        "- Do not invent evidence IDs. Only cite evidence_ids from the list provided below.\n"
        "- Do not make final buyer quote decisions.\n"
        "- Do not place orders.\n"
        "- Do not make payment instructions.\n"
        "- Human approval is required before any buyer-facing quote dispatch.\n"
        "\n"
        "TASK:\n"
        "Analyze the product requirement and the provided evidence samples.\n"
        "Assess whether the evidence is comparable to the requirement.\n"
        "Return a JSON object with these fields:\n"
        "  - normalized_product_type: string\n"
        "  - normalized_material: string or null\n"
        "  - normalized_process_tags: list of strings\n"
        "  - is_comparable: boolean\n"
        "  - comparability_score: float between 0.0 and 1.0\n"
        "  - detected_mismatch_flags: list of strings\n"
        "  - evidence_ids: list of evidence IDs from the provided evidence (cite only real IDs)\n"
        "  - reason: string explaining your assessment\n"
        '  - confidence: "low", "medium", or "high"\n'
        "\n"
        "REQUIREMENT:\n"
        + json.dumps(payload.get("requirement", {}), ensure_ascii=False, indent=2)
        + "\n\nSUPPLIER QUOTE:\n"
        + json.dumps(payload.get("supplier_quote"), ensure_ascii=False, indent=2)
        + "\n\nEVIDENCE (cite only these IDs):\n"
        + json.dumps(payload.get("evidence", []), ensure_ascii=False, indent=2)
        + "\n\nAvailable evidence_ids: "
        + json.dumps(sorted(payload.get("evidence_ids", [])), ensure_ascii=False)
        + "\n\nReturn JSON only:"
    )
