"""Seed canonical GPM E2E pricing evidence into giraffe-db.

Seeds 20 comparable pricing evidence records (sufficient for high-confidence benchmark)
plus a project, RFQ, supplier response, and supplier response packet.

Requires a running giraffe-db instance:
    GIRAFFE_DB_BASE_URL=http://127.0.0.1:8001
    GPM_GIRAFFE_DB_TENANT_ID=tenant_gpm_e2e_001  (optional, defaults below)

Usage:
    GIRAFFE_DB_BASE_URL=http://127.0.0.1:8001 uv run python scripts/seed_gpm_e2e_canonical_evidence.py

With sufficient evidence (20 samples, supplier_quote.unit_price=3.78 USD inside the
P50–P75 high band) the live giraffe-db + Qwen path returns:
    supplier_quote_position: within_high_range
    recommendation: negotiate
    confidence: high
"""
from __future__ import annotations

import os
import sys

import httpx

GIRAFFE_DB_BASE_URL = os.environ.get("GIRAFFE_DB_BASE_URL", "http://127.0.0.1:8001")
TENANT_ID = os.environ.get("GPM_GIRAFFE_DB_TENANT_ID", "tenant_gpm_e2e_001")
PROJECT_EXTERNAL_ID = "project_gpm_e2e_shirts_001"
RFQ_EXTERNAL_ID = "rfq_gpm_e2e_shirts_001"

# 20 benchmark samples: price_min from 3.200 to 3.998 USD → P50≈3.599, P75≈3.799
# Supplier quote at 3.78 USD sits between P50 and P75 → within_high_range → negotiate
_CANONICAL_PRICES_USD = [round(3.20 + i * 0.042, 3) for i in range(20)]


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Giraffe-Tenant-ID": TENANT_ID,
    }


def post(client: httpx.Client, path: str, payload: dict) -> dict:
    r = client.post(path, json=payload, headers=_headers())
    if r.is_error:
        print(f"  ERROR {r.status_code} POST {path}: {r.text[:200]}")
        sys.exit(1)
    return r.json()


def get(client: httpx.Client, path: str) -> dict:
    r = client.get(path, headers=_headers())
    if r.is_error:
        print(f"  ERROR {r.status_code} GET {path}: {r.text[:200]}")
        sys.exit(1)
    return r.json()


def main() -> None:
    base = GIRAFFE_DB_BASE_URL.rstrip("/")
    print(f"giraffe-db: {base}")
    print(f"tenant:     {TENANT_ID}")
    print()

    with httpx.Client(base_url=base, timeout=30.0) as client:
        # Health check
        h = get(client, "/healthz")
        print(f"[healthz] {h.get('status', '?')}")

        # Project
        print("[project] creating...")
        proj = post(client, "/api/data/projects", {
            "external_id": PROJECT_EXTERNAL_ID,
            "name": "GPM E2E 10k Shirts (Canonical 20-sample Benchmark)",
            "tenant_id": TENANT_ID,
        })
        project_id = proj["id"]
        print(f"  project_id: {project_id}")

        # RFQ
        print("[rfq] creating...")
        rfq = post(client, "/api/data/rfqs", {
            "external_id": RFQ_EXTERNAL_ID,
            "project_id": project_id,
            "tenant_id": TENANT_ID,
            "product": "men cotton shirt",
            "quantity": 10000,
            "unit": "piece",
            "material": "100% cotton",
            "process_tags": ["cutting", "sewing", "buttoning", "packing"],
            "target_market": "Japan",
            "source_platform": "mock_1688",
        })
        rfq_id = rfq["id"]
        print(f"  rfq_id: {rfq_id}")

        # Pricing evidence — 20 canonical samples
        print("[evidence] seeding 20 canonical benchmark samples...")
        evidence_ids = []
        for i, price in enumerate(_CANONICAL_PRICES_USD):
            ev = post(client, "/api/data/gpm/pricing-evidence", {
                "external_id": f"ev-e2e-canonical-{i+1:03d}",
                "tenant_id": TENANT_ID,
                "source_type": "public_benchmark",
                "source_id": f"mock_1688_canonical_{i+1:03d}",
                "source_platform": "mock_1688",
                "rfq_id": rfq_id,
                "usable_for_benchmark": True,
                "payload": {
                    "product_title": f"men cotton shirt OEM canonical {i+1}",
                    "price_min": str(price),
                    "price_currency": "USD",
                    "price_unit": "piece",
                    "moq": "1000",
                    "material": "100% cotton",
                    "source_platform": "mock_1688",
                },
            })
            evidence_ids.append(ev["id"])
        print(f"  evidence_ids: {len(evidence_ids)} records")

        # Supplier response
        print("[supplier_response] creating...")
        sr = post(client, "/api/data/supplier-responses", {
            "rfq_id": rfq_id,
            "tenant_id": TENANT_ID,
            "supplier_name": "SupplierAlpha Canonical",
        })
        sr_id = sr["id"]
        print(f"  supplier_response_id: {sr_id}")

        # Supplier response packet
        print("[supplier_response_packet] creating...")
        srp = post(client, "/api/data/supplier-response-packets", {
            "supplier_response_id": sr_id,
            "tenant_id": TENANT_ID,
            "payload": {
                "supplier_quote": {
                    "unit_price": 3.78,
                    "currency": "USD",
                    "moq": 1000,
                },
            },
        })
        print(f"  supplier_response_packet_id: {srp['id']}")

        # Context bundle
        print("[gpm_context] creating bundle...")
        bundle = post(client, "/api/data/gpm/context", {
            "tenant_id": TENANT_ID,
            "project_id": project_id,
            "rfq_id": rfq_id,
            "supplier_response_id": sr_id,
            "evidence_ids": evidence_ids,
            "include_private_data": True,
        })
        print(f"  bundle_id: {bundle.get('id', bundle.get('bundle_id', '?'))}")

    print()
    print("SEED COMPLETE")
    print(f"tenant_id:    {TENANT_ID}")
    print(f"project_id:   {project_id}")
    print(f"rfq_id:       {rfq_id}")
    print(f"evidence:     {len(evidence_ids)} canonical benchmark samples")
    print(f"price range:  {_CANONICAL_PRICES_USD[0]:.3f}–{_CANONICAL_PRICES_USD[-1]:.3f} USD")
    print(f"supplier_quote: 3.78 USD (P50 < 3.78 <= P75 → within_high_range → negotiate)")
    print()
    print("To run the full E2E with giraffe-db retriever:")
    print(f"  GPM_CONTEXT_RETRIEVER=giraffe_db \\")
    print(f"  GPM_GIRAFFE_DB_BASE_URL={GIRAFFE_DB_BASE_URL} \\")
    print(f"  GPM_GIRAFFE_DB_TENANT_ID={TENANT_ID} \\")
    print(f"  GPM_GIRAFFE_DB_PROJECT_ID={project_id} \\")
    print(f"  GPM_GIRAFFE_DB_RFQ_ID={rfq_id} \\")
    print(f"  GPM_GIRAFFE_DB_INCLUDE_PRIVATE_DATA=true \\")
    print(f"  uv run python scripts/run_gpm_giraffe_db_context_smoke.py")


if __name__ == "__main__":
    main()
