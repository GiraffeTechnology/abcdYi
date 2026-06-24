from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.gpm.context.gpm_context_bundle import GPMContextBundle


@runtime_checkable
class GPMContextRetriever(Protocol):
    """Protocol for all Session E context retrievers."""

    def retrieve(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        rfq_id: str | None = None,
        supplier_response_id: str | None = None,
        include_private_data: bool | None = None,
        evidence_ids: list[str] | None = None,
    ) -> GPMContextBundle: ...
