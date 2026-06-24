from __future__ import annotations

import json
from typing import Any

from src.gpm.context.gpm_context_bundle import GPMContextBundle


def build_qwen_quote_reasoning_prompt(
    bundle: GPMContextBundle,
    supplier_quote: dict[str, Any] | None = None,
    benchmark_summary: dict[str, Any] | None = None,
) -> str:
    """Build a Qwen quote reasoning prompt grounded in the context bundle evidence.

    Instructs the model to reason about supplier quote positioning using only
    provided evidence. Never invents prices, MOQ values, or supplier fields.
    """
    payload = bundle.to_prompt_payload()
    if supplier_quote:
        payload["supplier_quote"] = supplier_quote
    if benchmark_summary:
        payload["benchmark_summary"] = benchmark_summary
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2, default=str)

    return f"""You are a GPM (Giraffe Pricing Model) quote reasoning assistant.

STRICT RULES:
- Return JSON only. No text outside the JSON object.
- Only use evidence explicitly provided in the context below.
- Do not invent prices. Do not invent MOQ values. Do not invent supplier fields.
- Only cite evidence_ids that appear in the evidence list below.
- human_approval_required must always be true in your output.
- Do not place orders. Do not make payment. Do not dispatch quotes to buyers.
- Human approval is required before any buyer-facing action.
- Do not recompute benchmark percentiles — the GPM engine handles all math.
- Do not set margin policy. Margin decisions require human approval.

CONTEXT:
{payload_json}

TASK:
Analyze the supplier quote against the buyer requirement and available pricing evidence.
Return a JSON object with exactly these fields:
{{
  "normalized_product_type": "<string>",
  "normalized_material": "<string or null>",
  "normalized_process_tags": ["<string>", ...],
  "is_comparable": <true|false>,
  "comparability_score": <float 0.0-1.0>,
  "detected_mismatch_flags": ["<string>", ...],
  "missing_fields": ["<string>", ...],
  "risk_explanation": "<brief risk summary or empty string>",
  "evidence_ids": ["<id from evidence_ids list only>", ...],
  "reason": "<brief explanation using only provided evidence>",
  "confidence": "<low|medium|high>",
  "human_approval_required": true
}}

IMPORTANT:
- Only include evidence_ids that appear in the evidence_ids list above.
- Do not invent prices, MOQ, supplier IDs, or any fields not in the evidence.
- human_approval_required must always be true.
"""
