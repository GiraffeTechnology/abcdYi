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


class ContextRetriever(Protocol):
    """Structured retriever protocol for GPM context bundles."""

    def build_gpm_context(
        self,
        *,
        tenant_id: str | None,
        project_id: str | None,
        rfq_id: str | None,
        supplier_response_id: str | None,
        include_private_data: bool = False,
    ) -> GPMContextBundle: ...
