from __future__ import annotations

import json

from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.models.benchmark_snapshot import GPMBenchmarkSnapshot


def build_qwen_quote_reasoning_prompt(
    context: GPMContextBundle,
    benchmark: GPMBenchmarkSnapshot,
    supplier_quote: dict,
) -> str:
    """Build a quote reasoning explanation prompt for a local Qwen runtime.

    Qwen may explain why a quote is high/low relative to benchmark.
    Qwen must not compute benchmark math, set margin policy, or approve dispatch.
    """
    return (
        "You are a pricing intelligence assistant for GPM (Giraffe Pricing Model).\n"
        "\n"
        "STRICT RULES:\n"
        "- You may explain why the supplier quote is high or low relative to benchmark.\n"
        "- Do not compute benchmark percentiles or benchmark math. The benchmark is pre-calculated.\n"
        "- Do not set final margin policy.\n"
        "- Do not approve external dispatch or buyer-facing quote delivery.\n"
        "- Do not place orders.\n"
        "- Do not make payment instructions.\n"
        "- Human approval is required before any quote dispatch.\n"
        "- Return JSON only.\n"
        "\n"
        "TASK:\n"
        "Explain in plain language why the supplier quote is positioned relative to the benchmark.\n"
        "Return a JSON object with:\n"
        "  - quote_position_explanation: string (1-3 sentences)\n"
        "  - risk_factors: list of strings\n"
        '  - confidence: "low", "medium", or "high"\n'
        "\n"
        "BENCHMARK SUMMARY:\n"
        f"  - benchmark_id: {benchmark.id}\n"
        f"  - benchmark_low (p25): {benchmark.benchmark_low}\n"
        f"  - benchmark_median (p50): {benchmark.benchmark_median}\n"
        f"  - benchmark_high (p75): {benchmark.benchmark_high}\n"
        f"  - comparable_sample_count: {benchmark.comparable_sample_count}\n"
        f"  - confidence_level: {benchmark.confidence_level}\n"
        "\nSUPPLIER QUOTE:\n"
        + json.dumps(supplier_quote, ensure_ascii=False, indent=2)
        + "\n\nReturn JSON only:"
    )
