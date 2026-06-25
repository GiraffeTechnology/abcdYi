#!/usr/bin/env python3
"""Smoke test: GPM API service — runs in-process, no server required.

Usage:
    GPM_CONTEXT_RETRIEVER=mock GPM_RUNTIME_PROFILE=ci \
        python scripts/run_gpm_api_service_smoke.py
"""
import os
import sys

os.environ.setdefault("GPM_CONTEXT_RETRIEVER", "mock")
os.environ.setdefault("GPM_RUNTIME_PROFILE", "ci")

from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402

client = TestClient(app)
FAILED = 0


def check(label: str, ok: bool, detail: str = "") -> bool:
    global FAILED
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {label}{f': {detail}' if detail else ''}")
    if not ok:
        FAILED += 1
    return ok


def main() -> None:
    check("GET /api/gpm/healthz",
          client.get("/api/gpm/healthz").status_code == 200)
    check("GET /api/gpm/capabilities",
          client.get("/api/gpm/capabilities").status_code == 200)

    r = client.post("/api/gpm/quote-guidance", json={
        "tenant_id": "smoke-tenant",
        "rfq_id": "smoke-rfq-001",
        "supplier_response_id": "smoke-sr-001",
        "include_private_data": False,
    })
    if check("POST /api/gpm/quote-guidance", r.status_code == 201, r.text[:120]):
        pid = r.json()["packet"]["packet_id"]
        print(f"       packet_id: {pid}")
        print(f"       approval_status: {r.json()['packet']['approval_status']}")
        print(f"       human_approval_required: {r.json()['packet']['human_approval_required']}")

        check(f"GET /quote-guidance/{pid}",
              client.get(f"/api/gpm/quote-guidance/{pid}").status_code == 200)

        apr = client.post(f"/api/gpm/quote-guidance/{pid}/approve", json={
            "operator_id": "smoke-operator", "approval_note": "Smoke test",
        })
        if check("POST .../approve", apr.status_code == 200):
            print(f"       dispatched: {apr.json()['dispatched']}")

        r2 = client.post("/api/gpm/quote-guidance", json={"rfq_id": "smoke-rfq-002"})
        if r2.status_code == 201:
            pid2 = r2.json()["packet"]["packet_id"]
            check("POST .../reject",
                  client.post(f"/api/gpm/quote-guidance/{pid2}/reject",
                              json={"operator_id": "smoke-operator"}).status_code == 200)

    print(f"\n{'=' * 40}")
    if FAILED == 0:
        print("All smoke checks PASSED.")
    else:
        print(f"{FAILED} smoke check(s) FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
