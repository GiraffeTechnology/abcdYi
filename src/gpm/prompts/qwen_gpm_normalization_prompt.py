from __future__ import annotations

import json

from src.gpm.context.gpm_context_bundle import GPMContextBundle


def build_qwen_gpm_normalization_prompt(context: GPMContextBundle) -> str:
    """Build a Qwen normalization prompt grounded in the context bundle evidence."""
    payload = context.to_prompt_payload()
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    return f"""You are a GPM (Giraffe Pricing Model) normalization assistant.

STRICT RULES:
- Return JSON only. No text outside the JSON object.
- Only use evidence explicitly provided in the context below.
- Do not invent prices. Do not invent MOQ values. Do not invent supplier fields.
- Do not invent lead-time fields or missing data.
- Only cite evidence_ids that appear in the evidence list below.
- Require JSON output only. No markdown. No prose.
- human_approval_required must always be true in your output.
- Do not place orders. Do not make payment. Do not dispatch quotes to buyers.
- Human approval is required before any buyer-facing action.

CONTEXT:
{payload_json}

TASK:
Analyze the pricing evidence against the buyer requirement.
Determine if the supplier evidence is comparable to the requirement.
Return a JSON object with exactly these fields:
{{
  "normalized_product_type": "<string>",
  "normalized_material": "<string or null>",
  "normalized_process_tags": ["<string>", ...],
  "is_comparable": <true|false>,
  "comparability_score": <float 0.0-1.0>,
  "detected_mismatch_flags": ["<string>", ...],
  "evidence_ids": ["<id from evidence_ids list only>", ...],
  "reason": "<brief explanation using only provided evidence>",
  "confidence": "<low|medium|high>"
}}

IMPORTANT:
- Only include evidence_ids that appear in the evidence_ids list above.
- Do not invent prices, MOQ, supplier IDs, or any fields not in the evidence.
- Do not compute benchmark percentiles or set margin policy.
- Do not compute benchmark percentiles — the GPM engine handles all math.
"""
