#!/usr/bin/env python3
"""Smoke test: GPM OpenClaw skill contract — validates TypeScript skill API shape.

Tests the GPM API endpoints that the OpenClaw skill calls, verifying the
expected input/output shapes without executing TypeScript.

Usage:
    GPM_CONTEXT_RETRIEVER=mock GPM_RUNTIME_PROFILE=ci \
        python scripts/run_gpm_openclaw_skill_smoke.py
"""
import os
import sys

os.environ.setdefault("GPM_CONTEXT_RETRIEVER", "mock")
os.environ.setdefault("GPM_RUNTIME_PROFILE", "ci")

from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402

client = TestClient(app)
FAILED = 0


def check(label: str, condition: bool) -> None:
    global FAILED
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}")
    if not condition:
        FAILED += 1


def main() -> None:
    r = client.post("/api/gpm/quote-guidance", json={
        "tenant_id": "openclaw-tenant",
        "operator_id": "openclaw-operator",
        "rfq_id": "rfq-openclaw-001",
        "supplier_response_id": "sr-openclaw-001",
        "include_private_data": True,
        "request_context": {"source": "openclaw"},
    })
    check("Skill: createQuoteGuidance → 201", r.status_code == 201)
    if r.status_code != 201:
        print(f"  {r.text[:200]}")
        sys.exit(1)

    packet = r.json()["packet"]
    pid = packet["packet_id"]

    check("Packet: human_approval_required=True", packet["human_approval_required"] is True)
    check("Packet: approval_status=pending", packet["approval_status"] == "pending")
    check("Response: operator_action_required present", "operator_action_required" in r.json())
    check("Packet: no order/dispatch fields",
          not {"order_id", "payment_id", "dispatch_ref"} & set(packet.keys()))

    get_r = client.get(f"/api/gpm/quote-guidance/{pid}")
    check("Skill: getQuoteGuidance → 200", get_r.status_code == 200)

    apr = client.post(f"/api/gpm/quote-guidance/{pid}/approve", json={
        "operator_id": "openclaw-operator",
        "approval_note": "Skill smoke approval",
        "selected_option_id": "opt_accept",
    })
    check("Skill: approveQuoteGuidance → 200", apr.status_code == 200)
    check("Approval: dispatched=False", apr.json()["dispatched"] is False)
    check("Approval: No auto-execution note",
          "No external action" in apr.json()["dispatch_note"])

    print(f"\n{'=' * 40}")
    if FAILED == 0:
        print("All OpenClaw skill contract checks PASSED.")
    else:
        print(f"{FAILED} check(s) FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
