"""Mock BOM parser — reads BOM fixture metadata."""
import json
from pathlib import Path


def parse_bom_file(file_ref: str) -> dict:
    """Return structured metadata from a BOM file reference."""
    path = Path(file_ref)
    if path.exists() and path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "source_type": "bom",
        "part_summary": f"BOM assembly from {file_ref}",
        "components": [],
        "material": None,
    }
