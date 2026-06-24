"""GiraffeDBContextRetriever: HTTP-backed retriever using GiraffeDBClient. No fallback on failure."""
from __future__ import annotations

from src.gpm.clients.giraffe_db_client import GiraffeDBClient
from src.gpm.context.gpm_context_bundle import GPMContextBundle
from src.gpm.context.mappers.giraffe_db_context_mapper import GiraffeDBContextMapper


class GiraffeDBContextRetriever:
    """Calls giraffe-db /gpm/context and maps the response to GPMContextBundle.

    Raises GiraffeDBClientError if giraffe-db is unreachable — never falls back to mock.
    """

    def __init__(
        self,
        client: GiraffeDBClient,
        default_tenant_id: str | None = None,
        include_private_data: bool = False,
    ) -> None:
        self._client = client
        self._default_tenant_id = default_tenant_id
        self._default_include_private_data = include_private_data
        self._mapper = GiraffeDBContextMapper()

    def retrieve(
        self,
        *,
        tenant_id: str | None = None,
        project_id: str | None = None,
        rfq_id: str | None = None,
        supplier_response_id: str | None = None,
        include_private_data: bool | None = None,
        evidence_ids: list[str] | None = None,
    ) -> GPMContextBundle:
        effective_tenant_id = tenant_id or self._default_tenant_id
        effective_include_private = (
            include_private_data
            if include_private_data is not None
            else self._default_include_private_data
        )

        payload: dict = {"include_private_data": effective_include_private}
        if effective_tenant_id:
            payload["tenant_id"] = effective_tenant_id
        if project_id:
            payload["project_id"] = project_id
        if rfq_id:
            payload["rfq_id"] = rfq_id
        if supplier_response_id:
            payload["supplier_response_id"] = supplier_response_id
        if evidence_ids:
            payload["evidence_ids"] = evidence_ids

        response = self._client.create_gpm_context(payload)
        return self._mapper.map(response, include_private_data=effective_include_private)

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
