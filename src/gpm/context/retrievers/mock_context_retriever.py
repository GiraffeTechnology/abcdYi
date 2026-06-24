"""New-namespace MockContextRetriever: wraps the legacy implementation, adds retrieve()."""
from __future__ import annotations

from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.context.mock_context_retriever import MockContextRetriever as _LegacyMockContextRetriever


class MockContextRetriever:
    """Deterministic mock retriever satisfying the Session E retrieve() interface."""

    def __init__(self) -> None:
        self._legacy = _LegacyMockContextRetriever()

    def retrieve(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        rfq_id: str | None = None,
        supplier_response_id: str | None = None,
        include_private_data: bool = False,
        evidence_ids: list[str] | None = None,
    ) -> GPMContextBundle:
        return self._legacy.build_gpm_context(
            tenant_id=tenant_id,
            project_id=project_id,
            rfq_id=rfq_id,
            supplier_response_id=supplier_response_id,
            include_private_data=include_private_data,
        )

    def build_gpm_context(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        rfq_id: str | None = None,
        supplier_response_id: str | None = None,
        include_private_data: bool = False,
    ) -> GPMContextBundle:
        return self.retrieve(
            tenant_id=tenant_id,
            project_id=project_id,
            rfq_id=rfq_id,
            supplier_response_id=supplier_response_id,
            include_private_data=include_private_data,
        )
