#!/usr/bin/env python3
"""
GPM Real-Data Availability Test Pipeline — Batch Loader from File

Loads a JSON backup produced by collect_qwen_data.py into the database.
Use this when collect_qwen_data.py saved records to file but DB was unavailable.

Usage:
    SKIP_HUMAN_REVIEW=true APP_ENV=staging uv run python gpm/scripts/load_batch_from_file.py <path_to_backup.json>
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from gpm.config import GPMSettings
from gpm.db import AsyncSessionLocal
from gpm.service import submit_test_batch


async def load_from_file(backup_path: Path, cfg: GPMSettings) -> None:
    with backup_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    batch_id = data["batch_id"]
    records = data["records"]

    print(f"[load_batch_from_file] batch_id={batch_id}")
    print(f"[load_batch_from_file] Loading {len(records)} records into DB...")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            count = await submit_test_batch(session, records, batch_id, cfg=cfg)

    print(f"[load_batch_from_file] Successfully inserted {count} records.")
    print(f"[load_batch_from_file] batch_id={batch_id}")


def main() -> None:
    if len(sys.argv) < 2:
        print(
            "Usage: SKIP_HUMAN_REVIEW=true APP_ENV=staging uv run python "
            "gpm/scripts/load_batch_from_file.py <path_to_backup.json>",
            file=sys.stderr,
        )
        sys.exit(1)

    cfg = GPMSettings()

    if not cfg.SKIP_HUMAN_REVIEW:
        print("ERROR: SKIP_HUMAN_REVIEW must be 'true'.", file=sys.stderr)
        sys.exit(1)

    if cfg.APP_ENV == "production":
        print("ERROR: Cannot run in production.", file=sys.stderr)
        sys.exit(1)

    backup_path = Path(sys.argv[1])
    if not backup_path.exists():
        print(f"ERROR: File not found: {backup_path}", file=sys.stderr)
        sys.exit(1)

    asyncio.run(load_from_file(backup_path, cfg))


if __name__ == "__main__":
    main()
