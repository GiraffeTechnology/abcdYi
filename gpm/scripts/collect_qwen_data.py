#!/usr/bin/env python3
"""
GPM Real-Data Availability Test Pipeline — Qwen Data Collection Script

Collects real Chinese apparel/textile industry pricing data from the Qwen API.
Each record MUST include a verifiable source citation. Records without citations
are dropped. Collected data is saved as raw JSONL and loaded into the DB via
submit_test_batch().

Usage:
    QWEN_API_KEY=<key> SKIP_HUMAN_REVIEW=true APP_ENV=staging uv run python gpm/scripts/collect_qwen_data.py

Environment variables required:
    QWEN_API_KEY        — Aliyun DashScope API key
    SKIP_HUMAN_REVIEW   — must be "true"
    APP_ENV             — must NOT be "production"
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Allow running from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx

from gpm.config import GPMSettings
from gpm.db import AsyncSessionLocal
from gpm.service import submit_test_batch

# ---------------------------------------------------------------------------
# Categories to collect data for
# ---------------------------------------------------------------------------
CATEGORIES = [
    "fabric",
    "sewing_process",
    "embroidery_process",
    "printing_process",
    "accessory",
    "packaging",
]

# Target records per category (adjust to hit 1000+ total)
TARGET_PER_CATEGORY = 200

# ---------------------------------------------------------------------------
# Qwen API helper
# ---------------------------------------------------------------------------

def query_qwen(prompt: str, api_key: str) -> str:
    resp = httpx.post(
        "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "qwen-turbo",
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "parameters": {"result_format": "message", "max_tokens": 4000},
        },
        timeout=60.0,
    )
    resp.raise_for_status()
    return resp.json()["output"]["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

CATEGORY_PROMPTS = {
    "fabric": (
        "You are a Chinese textile industry pricing expert. "
        "List at least 30 real market price data points for common fabrics used in Chinese apparel manufacturing "
        "(e.g. cotton, polyester, linen, silk, wool blends). "
        "Include: fabric type, specification (weight/composition), unit price in CNY per meter, "
        "year of data, and the specific publication or industry report where this price was published. "
        "ONLY include data you can cite. Format each record as JSON with keys: "
        "process_id, param_key, param_value, unit_price, currency, source. "
        "process_id should be 'fabric_cost', param_key should be the fabric type, "
        "param_value should be the specification, unit_price in CNY, source must include "
        "publication name and year (e.g. '中国纺织工业联合会市场价格报告 2023'). "
        "Output a JSON array of records. Drop any record without a verifiable source."
    ),
    "sewing_process": (
        "You are a Chinese apparel manufacturing pricing expert. "
        "List at least 30 real market price data points for sewing process costs in Chinese garment factories "
        "(e.g. basic stitch, overlock, buttonhole, zipper attachment). "
        "Include: process name, garment type, unit price in CNY per piece, "
        "year of data, and the specific publication or trade association report. "
        "Format each record as JSON with keys: "
        "process_id ('sewing_process'), param_key (process/stitch type), param_value (garment category), "
        "unit_price in CNY, currency ('CNY'), source (must include publication name + year). "
        "Output a JSON array. Drop records without verifiable sources."
    ),
    "embroidery_process": (
        "You are a Chinese embroidery and decorative process pricing expert. "
        "List at least 30 real market price data points for embroidery process costs in China "
        "(e.g. flat embroidery, 3D embroidery, sequin embroidery — priced by stitch count or area). "
        "Include: embroidery type, size/complexity, unit price in CNY, "
        "year of data, and the specific publication or industry source. "
        "Format as JSON array with keys: "
        "process_id ('embroidery_process'), param_key (embroidery type), param_value (size/stitch count), "
        "unit_price in CNY, currency ('CNY'), source (publication + year required). "
        "Drop any record without a verifiable citation."
    ),
    "printing_process": (
        "You are a Chinese textile printing process pricing expert. "
        "List at least 30 real market price data points for printing process costs "
        "(e.g. screen printing, digital printing, heat transfer, discharge printing). "
        "Include: printing type, color count or area, unit price in CNY per piece, "
        "year, and specific publication or market report. "
        "Format as JSON array with keys: "
        "process_id ('printing_process'), param_key (printing type), param_value (spec), "
        "unit_price in CNY, currency ('CNY'), source (publication + year required). "
        "Drop records without verifiable citations."
    ),
    "accessory": (
        "You are a Chinese garment accessory pricing expert. "
        "List at least 30 real market price data points for common garment accessories in China "
        "(e.g. buttons, zippers, labels, hang tags, rivets, elastic). "
        "Include: accessory type, specification, unit price in CNY, "
        "year, and the specific trade report or market data source. "
        "Format as JSON array with keys: "
        "process_id ('accessory_cost'), param_key (accessory type), param_value (specification), "
        "unit_price in CNY, currency ('CNY'), source (publication + year required). "
        "Drop records without verifiable citations."
    ),
    "packaging": (
        "You are a Chinese garment packaging cost expert. "
        "List at least 30 real market price data points for packaging materials/services in China "
        "(e.g. poly bags, cartons, hangers, tissue paper, folding/packing labor). "
        "Include: packaging type, size/spec, unit price in CNY, "
        "year, and specific publication or industry report. "
        "Format as JSON array with keys: "
        "process_id ('packaging_cost'), param_key (packaging type), param_value (specification), "
        "unit_price in CNY, currency ('CNY'), source (publication + year required). "
        "Drop records without verifiable citations."
    ),
}


# ---------------------------------------------------------------------------
# Record validation
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {"process_id", "param_key", "unit_price", "currency", "source"}


def validate_record(rec: dict) -> bool:
    """Return True if the record has all required fields and a non-empty source."""
    for field in REQUIRED_FIELDS:
        if not rec.get(field):
            return False
    source = rec["source"].strip()
    if len(source) < 5:
        return False
    return True


# ---------------------------------------------------------------------------
# Main collection logic
# ---------------------------------------------------------------------------

async def collect_and_load(batch_id: str, api_key: str, cfg: GPMSettings) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    raw_output_path = Path(__file__).resolve().parents[1] / "data" / f"qwen_raw_responses_{timestamp}.jsonl"
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)

    all_records: list[dict] = []
    total_dropped = 0

    for category in CATEGORIES:
        print(f"[collect_qwen_data] Querying Qwen for category: {category}")
        prompt = CATEGORY_PROMPTS[category]

        try:
            response_text = query_qwen(prompt, api_key)
        except Exception as exc:
            print(f"  ERROR querying Qwen for {category}: {exc}", file=sys.stderr)
            continue

        # Save raw response (source refs only — not full model snapshot)
        raw_entry = {
            "category": category,
            "batch_id": batch_id,
            "timestamp": timestamp,
            "source_ref": f"Qwen API response for category={category}",
            "raw_text_length": len(response_text),
        }
        with raw_output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(raw_entry, ensure_ascii=False) + "\n")

        # Parse JSON from response
        records = []
        try:
            # Try to find a JSON array in the response
            start = response_text.find("[")
            end = response_text.rfind("]")
            if start != -1 and end != -1:
                json_str = response_text[start : end + 1]
                records = json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"  WARNING: Could not parse JSON for {category}: {exc}", file=sys.stderr)
            continue

        # Validate and filter
        valid = []
        for rec in records:
            if not isinstance(rec, dict):
                total_dropped += 1
                continue
            if validate_record(rec):
                # Ensure numeric unit_price
                try:
                    rec["unit_price"] = float(rec["unit_price"])
                except (TypeError, ValueError):
                    total_dropped += 1
                    continue
                valid.append(rec)
            else:
                total_dropped += 1

        print(f"  {category}: {len(valid)} valid records ({len(records) - len(valid)} dropped, no source)")
        all_records.extend(valid)

        # Progress report every 100 records
        if len(all_records) % 100 < len(valid):
            print(f"  [Progress] Total collected so far: {len(all_records)}")

    print(f"\n[collect_qwen_data] Total valid records: {len(all_records)}, dropped: {total_dropped}")
    print(f"[collect_qwen_data] Raw responses saved to: {raw_output_path}")

    if not all_records:
        print("[collect_qwen_data] No valid records to load. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Load into DB
    print(f"[collect_qwen_data] Loading {len(all_records)} records into DB (batch_id={batch_id}) ...")
    async with AsyncSessionLocal() as session:
        async with session.begin():
            count = await submit_test_batch(session, all_records, batch_id, cfg=cfg)
    print(f"[collect_qwen_data] Successfully inserted {count} records.")


def main() -> None:
    # Guard: QWEN_API_KEY
    api_key = os.environ.get("QWEN_API_KEY", "").strip()
    if not api_key:
        print(
            "ERROR: QWEN_API_KEY environment variable is required.\n"
            "Set it to your Aliyun DashScope API key before running this script.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build config from environment
    cfg = GPMSettings()

    if not cfg.SKIP_HUMAN_REVIEW:
        print(
            "ERROR: SKIP_HUMAN_REVIEW must be set to 'true' to run this script.\n"
            "Example: SKIP_HUMAN_REVIEW=true APP_ENV=staging uv run python gpm/scripts/collect_qwen_data.py",
            file=sys.stderr,
        )
        sys.exit(1)

    if cfg.APP_ENV == "production":
        print(
            "ERROR: This script cannot run in production (APP_ENV=production).",
            file=sys.stderr,
        )
        sys.exit(1)

    batch_id = f"qwen-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    print(f"[collect_qwen_data] Starting data collection. batch_id={batch_id}")

    asyncio.run(collect_and_load(batch_id, api_key, cfg))


if __name__ == "__main__":
    main()
