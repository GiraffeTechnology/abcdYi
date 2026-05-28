"""Mock STEP file parser — reads STEP fixture metadata without real STEP engine."""
import json
from pathlib import Path


def parse_step_file(file_ref: str) -> dict:
    """Return structured metadata from a STEP file reference."""
    path = Path(file_ref)
    if path.exists() and path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "source_type": "step",
        "part_summary": f"STEP part from {file_ref}",
        "material": "steel",
        "dimensions": {"length_mm": 120, "width_mm": 90, "height_mm": 50},
        "operation_requirements": ["cnc_milling", "cnc_turning"],
        "tolerance_requirements": {"general_mm": 0.05},
    }
