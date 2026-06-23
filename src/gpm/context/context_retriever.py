from __future__ import annotations

from typing import Protocol

from .gpm_context_bundle import GPMContextBundle


class GPMContextRetriever(Protocol):
    """Protocol for building a GPMContextBundle from a data source."""

    def build_context(
        self,
        requirement: dict,
        supplier_quote: dict | None,
        data_mode: str = "mock",
        tenant_id: str | None = None,
        project_id: str | None = None,
        limit: int = 20,
    ) -> GPMContextBundle: ...
