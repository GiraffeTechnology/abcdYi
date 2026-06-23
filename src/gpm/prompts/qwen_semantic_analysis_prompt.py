from __future__ import annotations

import json

from src.gpm.context.gpm_context_bundle import GPMContextBundle


def build_qwen_semantic_analysis_prompt(context: GPMContextBundle) -> str:
    payload = context.to_prompt_payload()
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    return f"""You are a pricing intelligence assistant for GPM (Giraffe Pricing Model).

STRICT RULES:
- Return JSON only. No explanations outside the JSON object.
- Do not invent prices. Only reference prices explicitly present in the evidence.
- Do not invent MOQ values. Only reference MOQ values explicitly present in the evidence.
- Do not invent supplier IDs or evidence IDs. Only cite evidence_ids that appear in the context below.
- Do not make final buyer quote decisions.
- Do not place orders. Do not make payment. Do not dispatch quotes to buyers.
- Human approval is required before any external quote is sent.
- Focus on product comparability: does the supplier evidence match the buyer requirement?

CONTEXT:
{payload_json}

TASK:
Analyze the supplier evidence against the buyer requirement.
Return a JSON object with exactly these fields:
{{
  "normalized_product_type": "<string>",
  "normalized_material": "<string or null>",
  "normalized_process_tags": ["<string>", ...],
  "is_comparable": <true|false>,
  "comparability_score": <float 0.0-1.0>,
  "detected_mismatch_flags": ["<string>", ...],
  "evidence_ids": ["<id from context evidence_ids only>", ...],
  "reason": "<brief explanation>",
  "confidence": "<low|medium|high>"
}}

IMPORTANT: Only include evidence_ids that appear in the evidence_ids list above.
Do not invent new IDs.
"""
