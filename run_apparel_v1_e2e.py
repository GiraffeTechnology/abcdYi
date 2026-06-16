#!/usr/bin/env python3
"""
Apparel & Textile v1.0 E2E runnable script.

Runs the full 14-step procurement flow from buyer inquiry to buyer-facing
quotation with 3 options (A=fastest, B=cheapest, C=balanced/recommended).

Usage:
    python run_apparel_v1_e2e.py
    python run_apparel_v1_e2e.py --inquiry "custom inquiry text"
    python run_apparel_v1_e2e.py --json
    python run_apparel_v1_e2e.py --no-approve
"""
import argparse
import json
import sys

from src.apparel_v1.e2e_flow import run_apparel_v1_e2e, format_decision_packet
from src.apparel_v1.inquiry_intake import CANONICAL_INQUIRY


def _hr(char: str = "─", width: int = 72) -> str:
    return char * width


def print_header() -> None:
    print(_hr("="))
    print("  APPAREL & TEXTILE v1.0 — E2E PROCUREMENT FLOW")
    print(_hr("="))


def print_options(options: list[dict]) -> None:
    print(_hr())
    print("BUYER OPTIONS")
    print(_hr())
    for opt in options:
        feasible_str = "✓ FEASIBLE" if opt["feasible_for_deadline"] else "✗ OVER DEADLINE"
        slack = opt.get("slack_days")
        slack_str = f" (slack: {slack}d)" if slack is not None else ""
        print()
        print(f"  Option {opt['label']}: {opt['name']}")
        print(f"    Supplier     : {opt['supplier']} ({opt['location']})")
        print(f"    Quantity     : {opt['quantity']:,} pcs")
        print(f"    Unit Price   : USD {opt['unit_price_usd']:.2f}")
        print(f"    Total Price  : USD {opt['total_price_usd']:,.2f}")
        print(f"    Material     : {opt['material_lead_time_days']} days")
        print(f"    Production   : {opt['production_lead_time_days']} days")
        print(f"    Total LT     : {opt['total_lead_time_days']} days — {feasible_str}{slack_str}")
        if opt["risk_flags"]:
            flags = ", ".join(opt["risk_flags"][:3])
            print(f"    Risk Flags   : {flags}")
        milestones = ", ".join(m for m in opt["qc_milestones"][:3]) + " ..."
        print(f"    QC Milestones: {milestones}")
        print(f"    Approval     : {opt['human_approval_status'].upper()}")


def print_qc_summary(qc: dict) -> None:
    print()
    print(_hr())
    print("QC PROCESS CARD SUMMARY")
    print(_hr())
    print(f"  Standard          : {qc['standard']}")
    print(f"  Inspection Stages : {qc['inspection_stages']}")
    print(f"  Critical Defects  : {qc['critical_defect_categories']} categories (zero tolerance)")
    print(f"  Market Notes      : {qc['target_market_notes']}")


def print_execution_log(events: list) -> None:
    print()
    print(_hr())
    print("EXECUTION LOG")
    print(_hr())
    for evt in events:
        status_icon = "✓" if evt.status == "ok" else ("⚠" if evt.status == "warning" else "✗")
        print(f"  {status_icon} {evt.step}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Apparel & Textile v1.0 E2E Flow")
    parser.add_argument(
        "--inquiry",
        type=str,
        default=CANONICAL_INQUIRY,
        help="Buyer inquiry text (default: canonical cotton shirt inquiry)",
    )
    parser.add_argument(
        "--no-approve",
        action="store_true",
        help="Disable auto-approval of the human gate",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Output the decision packet as JSON",
    )
    args = parser.parse_args()

    auto_approve = not args.no_approve

    if not args.as_json:
        print_header()
        print()
        print(f"Buyer Inquiry:")
        print(f"  \"{args.inquiry}\"")
        print()

    try:
        result = run_apparel_v1_e2e(raw_inquiry=args.inquiry, auto_approve=auto_approve)
    except Exception as exc:
        print(f"\n[ERROR] Flow failed: {exc}", file=sys.stderr)
        return 1

    packet = format_decision_packet(result)

    if args.as_json:
        print(json.dumps(packet, indent=2, default=str))
        return 0

    # Human-readable output
    print(f"Flow ID          : {packet['flow_id']}")
    print(f"Quote ID         : {packet['quote_id']}")
    print(f"Product          : {packet['product_summary']}")
    print(f"Recommended      : Option {packet['recommended_option']}")
    print(f"Approval Status  : {packet['human_approval_status'].upper()}")
    print(f"Completeness     : {packet['completeness_score']:.0%}")
    print(f"Execution Steps  : {packet['execution_steps']}")
    if packet["missing_fields"]:
        print(f"Missing Fields   : {', '.join(packet['missing_fields'])}")

    print_options(packet["options"])

    if packet.get("qc_summary"):
        print_qc_summary(packet["qc_summary"])

    print_execution_log(result.execution_log)

    print()
    print(_hr("="))
    if result.status == "completed":
        print("  ✓ E2E flow completed successfully.")
    else:
        print(f"  ✗ Flow ended with status: {result.status}")
    print(_hr("="))

    return 0


if __name__ == "__main__":
    sys.exit(main())
