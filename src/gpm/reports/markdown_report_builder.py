from __future__ import annotations

from src.gpm.models.benchmark_snapshot import GPMBenchmarkSnapshot
from src.gpm.models.quote_guidance import GPMQuoteGuidance


class GPMMarkdownReportBuilder:
    def build_quote_guidance_report(
        self, guidance: GPMQuoteGuidance, benchmark: GPMBenchmarkSnapshot
    ) -> str:
        lines: list[str] = [
            "# GPM Lightweight Quote Guidance Report",
            "",
            "## Requirement Summary",
            f"- Requirement ID: {guidance.requirement_id or 'N/A'}",
            f"- Benchmark Snapshot ID: {guidance.benchmark_snapshot_id}",
            f"- Target Quantity: {benchmark.target_quantity} {benchmark.target_quantity_unit or ''}",
            "",
            "## Benchmark Range",
            f"- Confidence: **{benchmark.confidence_level}** ({benchmark.confidence_reason})",
            f"- Comparable Samples: {benchmark.comparable_sample_count} / {benchmark.sample_count}",
            f"- Benchmark Low (P25): {benchmark.benchmark_low}",
            f"- Benchmark Median (P50): {benchmark.benchmark_median}",
            f"- Benchmark High (P75): {benchmark.benchmark_high}",
            "",
            "## Supplier Quote",
            f"- Supplier ID: {guidance.supplier_id or 'N/A'}",
            f"- Quote Price: {guidance.supplier_quote_price} {guidance.supplier_quote_currency}/{guidance.supplier_quote_unit}",
            f"- MOQ: {guidance.supplier_quote_moq or 'N/A'}",
            "",
            "## Quote Position & Recommendation",
            f"- **Supplier Quote Position:** {guidance.supplier_quote_position}",
            f"- **Accept Recommendation:** {guidance.accept_recommendation}",
            f"- Suggested Counter Price: {guidance.recommended_counter_price or 'N/A'}",
            "",
            "## Buyer-Facing Quote Options",
            f"- Low Option: {guidance.recommended_buyer_quote_low}",
            f"- Mid Option: {guidance.recommended_buyer_quote_mid}",
            f"- High Option: {guidance.recommended_buyer_quote_high}",
            "",
            "## Risk Flags",
        ]

        if guidance.risk_flags:
            for flag in guidance.risk_flags:
                lines.append(f"- {flag}")
        else:
            lines.append("- None")

        lines += [
            "",
            "## Explanation",
            guidance.explanation,
            "",
            "---",
            "> **HUMAN APPROVAL REQUIRED** before accepting supplier quotes or sending buyer-facing quotes.",
        ]

        return "\n".join(lines)
