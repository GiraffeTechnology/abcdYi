"""Mock CAD file parser — reads CAD fixture metadata without real CAD engine."""
import json
from pathlib import Path


def parse_cad_file(file_ref: str) -> dict:
    """Return structured metadata from a CAD file reference (fixture path or mock)."""
    path = Path(file_ref)
    if path.exists() and path.suffix == ".json":
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Return a minimal mock for non-existent refs
    return {
        "source_type": "cad",
        "part_summary": f"Part from {file_ref}",
        "material": "aluminum",
        "dimensions": {"length_mm": 100, "width_mm": 80, "height_mm": 60},
        "operation_requirements": ["cnc_milling"],
        "tolerance_requirements": {"general_mm": 0.1},
    }
