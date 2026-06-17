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

# Target records per category (6 × 200 = 1200 total)
TARGET_PER_CATEGORY = 200

# Canonical process_id for each category
CATEGORY_TO_PROCESS_ID = {
    "fabric": "fabric_cost",
    "sewing_process": "sewing_process",
    "embroidery_process": "embroidery_process",
    "printing_process": "printing_process",
    "accessory": "accessory_cost",
    "packaging": "packaging_cost",
}

# Alternative field names Qwen may return instead of the canonical "param_key"
PARAM_KEY_ALIASES: dict[str, list[str]] = {
    "fabric": ["fabric_type", "fabric"],
    "sewing_process": ["sewing_process", "process/stitch_type", "stitch_type", "process_type"],
    "embroidery_process": ["embroidery_process", "embroidery_type", "type"],
    "printing_process": ["printing_process", "printing_type", "print_type", "type"],
    "accessory": ["accessory_type", "accessory", "type"],
    "packaging": ["packaging_type", "packaging", "type"],
}

# Alternative field names Qwen may return instead of "param_value"
PARAM_VALUE_ALIASES = [
    "param_value", "garment_category", "garment_type",
    "specification", "spec", "size_stitch_count", "description",
]


def normalize_record(rec: dict, category: str) -> dict:
    """Map non-standard Qwen field names to canonical GPM field names."""
    n = dict(rec)

    if not n.get("process_id"):
        n["process_id"] = CATEGORY_TO_PROCESS_ID.get(category, category)

    if not n.get("param_key"):
        for alias in PARAM_KEY_ALIASES.get(category, []):
            if n.get(alias):
                n["param_key"] = n[alias]
                break

    if not n.get("param_value"):
        for alias in PARAM_VALUE_ALIASES:
            if n.get(alias):
                n["param_value"] = n[alias]
                break

    return n


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
# Prompts — explicit about required JSON keys to reduce field-name drift
# ---------------------------------------------------------------------------

def _base_prompt(category_instruction: str, process_id: str, param_key_desc: str, param_value_desc: str) -> str:
    return (
        f"{category_instruction} "
        "Output ONLY a JSON array. Each element must be a JSON object with EXACTLY these keys: "
        f'"process_id" (string, set to "{process_id}"), '
        f'"param_key" ({param_key_desc}), '
        f'"param_value" ({param_value_desc}), '
        '"unit_price" (number, in CNY), '
        '"currency" (string, "CNY"), '
        '"source" (string: publication name + year, e.g. "中国纺织工业联合会市场价格报告 2023"). '
        "Do NOT use any other key names. Drop any record where source is empty or unverifiable. "
        "Include at least 30 records."
    )


CATEGORY_PROMPTS = {
    "fabric": _base_prompt(
        "You are a Chinese textile industry pricing expert. "
        "List real market price data points for common fabrics used in Chinese apparel manufacturing "
        "(cotton, polyester, linen, silk, wool blends, etc.). "
        "Each data point must cite a specific industry publication with year.",
        "fabric_cost",
        'fabric type (e.g. "cotton", "polyester", "silk")',
        'specification (e.g. "180g/m² 100% cotton", "75D polyester")',
    ),
    "sewing_process": _base_prompt(
        "You are a Chinese apparel manufacturing pricing expert. "
        "List real market price data points for sewing process costs in Chinese garment factories "
        "(basic stitch, overlock, buttonhole, zipper attachment, etc.). "
        "Each data point must cite a specific publication or trade association report with year.",
        "sewing_process",
        'stitch or process type (e.g. "basic_stitch", "overlock", "buttonhole")',
        'garment category (e.g. "T-shirt", "jeans", "jacket")',
    ),
    "embroidery_process": _base_prompt(
        "You are a Chinese embroidery pricing expert. "
        "List real market price data points for embroidery process costs in China "
        "(flat embroidery, 3D embroidery, sequin embroidery, etc.). "
        "Each data point must cite a specific publication or industry source with year.",
        "embroidery_process",
        'embroidery type (e.g. "flat_embroidery", "3d_embroidery", "sequin_embroidery")',
        'size or complexity (e.g. "5cm×5cm 5000 stitches", "10cm×10cm")',
    ),
    "printing_process": _base_prompt(
        "You are a Chinese textile printing pricing expert. "
        "List real market price data points for printing process costs in China "
        "(screen printing, digital printing, heat transfer, discharge printing, etc.). "
        "Each data point must cite a specific publication or market report with year.",
        "printing_process",
        'printing type (e.g. "screen_printing", "digital_printing", "heat_transfer")',
        'specification (e.g. "4-color 30×40cm", "A4 full-color digital")',
    ),
    "accessory": _base_prompt(
        "You are a Chinese garment accessory pricing expert. "
        "List real market price data points for common garment accessories in China "
        "(buttons, zippers, labels, hang tags, rivets, elastic, etc.). "
        "Each data point must cite a specific trade report or market data source with year.",
        "accessory_cost",
        'accessory type (e.g. "button", "zipper", "label", "rivet")',
        'specification (e.g. "15mm resin button", "30cm metal zipper YKK")',
    ),
    "packaging": _base_prompt(
        "You are a Chinese garment packaging cost expert. "
        "List real market price data points for packaging materials/services in China "
        "(poly bags, cartons, hangers, tissue paper, folding/packing labor, etc.). "
        "Each data point must cite a specific publication or industry report with year.",
        "packaging_cost",
        'packaging type (e.g. "poly_bag", "carton", "hanger", "tissue_paper")',
        'specification (e.g. "35×45cm OPP poly bag", "single-wall carton 40×30×25cm")',
    ),
}

# Variation suffixes to diversify repeated calls for the same category
_VARIATION_SUFFIXES = [
    " Focus on data from 2020-2022.",
    " Focus on data from 2021-2023.",
    " Focus on data from 2019-2021.",
    " Include niche or regional variations.",
    " Focus on premium/high-end segment data.",
    " Focus on mass-market/low-cost segment data.",
    " Include data from smaller regional markets.",
]


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
# Per-category collection loop (multiple calls until target reached)
# ---------------------------------------------------------------------------

def collect_category(
    category: str,
    api_key: str,
    raw_output_path: Path,
    batch_id: str,
    timestamp: str,
    target: int,
) -> tuple[list[dict], int]:
    """
    Call Qwen repeatedly for a single category until `target` valid records are
    collected or we've made MAX_CALLS attempts. Returns (valid_records, dropped).
    """
    MAX_CALLS = max(1, (target // 25) + 2)  # safety cap

    base_prompt = CATEGORY_PROMPTS[category]
    collected: list[dict] = []
    seen_keys: set[tuple] = set()  # deduplicate on (param_key, param_value, unit_price)
    total_dropped = 0
    call_num = 0

    while len(collected) < target and call_num < MAX_CALLS:
        suffix = _VARIATION_SUFFIXES[call_num % len(_VARIATION_SUFFIXES)] if call_num > 0 else ""
        prompt = base_prompt + suffix

        try:
            response_text = query_qwen(prompt, api_key)
        except Exception as exc:
            print(f"  WARNING: Qwen call {call_num + 1} for {category} failed: {exc}", file=sys.stderr)
            call_num += 1
            continue

        # Save raw metadata
        raw_entry = {
            "category": category,
            "batch_id": batch_id,
            "timestamp": timestamp,
            "call_num": call_num + 1,
            "source_ref": f"Qwen API response for category={category} call={call_num + 1}",
            "raw_text_length": len(response_text),
        }
        with raw_output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(raw_entry, ensure_ascii=False) + "\n")

        # Parse JSON array from response
        records = []
        try:
            start = response_text.find("[")
            end = response_text.rfind("]")
            if start != -1 and end != -1:
                records = json.loads(response_text[start : end + 1])
        except (json.JSONDecodeError, ValueError) as exc:
            print(f"  WARNING: JSON parse error for {category} call {call_num + 1}: {exc}", file=sys.stderr)
            call_num += 1
            continue

        # Normalize + validate
        new_valid = 0
        for rec in records:
            if not isinstance(rec, dict):
                total_dropped += 1
                continue

            rec = normalize_record(rec, category)

            if not validate_record(rec):
                total_dropped += 1
                continue

            try:
                rec["unit_price"] = float(rec["unit_price"])
            except (TypeError, ValueError):
                total_dropped += 1
                continue

            # Deduplicate
            dedup_key = (rec.get("param_key"), rec.get("param_value"), rec.get("unit_price"))
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            collected.append(rec)
            new_valid += 1

        print(
            f"  {category} [call {call_num + 1}]: +{new_valid} valid "
            f"(total={len(collected)}/{target})"
        )
        call_num += 1

    return collected, total_dropped


# ---------------------------------------------------------------------------
# Main collection logic
# ---------------------------------------------------------------------------

async def collect_and_load(batch_id: str, api_key: str, cfg: GPMSettings) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    raw_output_path = data_dir / f"qwen_raw_responses_{timestamp}.jsonl"
    backup_path = data_dir / f"qwen_collected_{batch_id}.json"

    all_records: list[dict] = []
    total_dropped = 0

    for category in CATEGORIES:
        print(f"\n[collect_qwen_data] Category: {category} (target={TARGET_PER_CATEGORY})")
        cat_records, cat_dropped = collect_category(
            category, api_key, raw_output_path, batch_id, timestamp, TARGET_PER_CATEGORY
        )
        all_records.extend(cat_records)
        total_dropped += cat_dropped
        print(f"  → {len(cat_records)} valid records for {category}")

    print(f"\n[collect_qwen_data] Total valid records: {len(all_records)}, dropped: {total_dropped}")
    print(f"[collect_qwen_data] Raw response log: {raw_output_path}")

    if not all_records:
        print("[collect_qwen_data] No valid records to load. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Save JSON backup before attempting DB insert (records are never lost on DB failure)
    with backup_path.open("w", encoding="utf-8") as f:
        json.dump({"batch_id": batch_id, "records": all_records}, f, ensure_ascii=False, indent=2)
    print(f"[collect_qwen_data] Backup saved to: {backup_path}")

    # Load into DB
    print(f"[collect_qwen_data] Loading {len(all_records)} records into DB (batch_id={batch_id}) ...")
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                count = await submit_test_batch(session, all_records, batch_id, cfg=cfg)
        print(f"[collect_qwen_data] Successfully inserted {count} records.")
        print(f"[collect_qwen_data] batch_id={batch_id}")
    except Exception as exc:
        print(
            f"\n[collect_qwen_data] DB insert failed: {exc}\n"
            f"  Records are preserved in: {backup_path}\n"
            f"  To load later, run:\n"
            f"    uv run python gpm/scripts/load_batch_from_file.py {backup_path}",
            file=sys.stderr,
        )
        print(f"\n[collect_qwen_data] batch_id={batch_id}")
        print(f"[collect_qwen_data] {len(all_records)} records saved to file. DB load skipped.")


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
