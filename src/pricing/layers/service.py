"""
Asset layer resolution — client proprietary layer overrides universal layer.
Physical isolation between layers is enforced at the database schema level
(separate tables / schemas); this module only implements the merge logic.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional


def resolve_benchmark_value(
    universal_value: Optional[Decimal],
    client_value: Optional[Decimal],
    client_id: Optional[str],
) -> tuple[Optional[Decimal], str]:
    """
    Returns (resolved_value, source_label).
    Client proprietary layer takes priority when available (per spec §5).
    Falls back to giraffe_universal when no client-specific value exists.
    """
    if client_id and client_value is not None:
        return client_value, "client_proprietary"
    if universal_value is not None:
        return universal_value, "giraffe_universal"
    return None, "no_data"
