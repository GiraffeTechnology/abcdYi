from __future__ import annotations

from typing import Protocol

from src.gpm.context.gpm_context_bundle import GPMContextBundle


class GPMContextRetriever(Protocol):
    def build_context(
        self,
        requirement: dict,
        supplier_quote: dict | None,
        data_mode: str = "mock",
        tenant_id: str | None = None,
        project_id: str | None = None,
        limit: int = 20,
    ) -> GPMContextBundle: ...
