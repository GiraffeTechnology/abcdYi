from __future__ import annotations

import json

from src.gpm.context.gpm_context_bundle import GPMContextBundle


def build_qwen_quote_reasoning_prompt(
    context: GPMContextBundle,
    supplier_quote: dict,
    benchmark_summary: dict,
) -> str:
    payload = context.to_prompt_payload()
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    quote_json = json.dumps(supplier_quote, ensure_ascii=False, indent=2, default=str)
    bench_json = json.dumps(benchmark_summary, ensure_ascii=False, indent=2, default=str)

    return f"""You are a pricing intelligence assistant for GPM (Giraffe Pricing Model).

STRICT RULES:
- Return JSON only. No explanations outside the JSON object.
- Do not compute benchmark percentiles. The benchmark is already computed below.
- Do not set final margin policy.
- Do not approve external quote dispatch.
- Do not place orders. Do not make payment.
- Human approval is required before any buyer-facing quote is dispatched.
- You may explain why the supplier quote is high or low relative to the benchmark.
- Do not invent prices or MOQ values not present in the evidence.

CONTEXT:
{payload_json}

SUPPLIER QUOTE:
{quote_json}

BENCHMARK SUMMARY (computed by deterministic GPM engine — do not recompute):
{bench_json}

TASK:
Explain why the supplier quote is positioned as described.
Return a JSON object with exactly these fields:
{{
  "quote_position_explanation": "<brief explanation>",
  "risk_factors": ["<string>", ...],
  "evidence_ids": ["<id from context evidence_ids only>", ...],
  "human_approval_required": true
}}

IMPORTANT: human_approval_required must always be true.
Do not override GPM benchmark or margin policy calculations.
"""
