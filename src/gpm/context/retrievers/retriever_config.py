"""Factory that reads GPM_CONTEXT_RETRIEVER env and returns the appropriate retriever."""
from __future__ import annotations

import os

from src.gpm.clients.giraffe_db_client import GiraffeDBClient
from src.gpm.context.retrievers.giraffe_db_context_retriever import GiraffeDBContextRetriever
from src.gpm.context.retrievers.mock_context_retriever import MockContextRetriever


def build_context_retriever_from_env() -> MockContextRetriever | GiraffeDBContextRetriever:
    """Build a context retriever from environment variables.

    GPM_CONTEXT_RETRIEVER=mock (default)  -> MockContextRetriever  (CI-safe, no network)
    GPM_CONTEXT_RETRIEVER=giraffe_db      -> GiraffeDBContextRetriever (requires GPM_GIRAFFE_DB_BASE_URL)

    When GPM_CONTEXT_RETRIEVER=giraffe_db and giraffe-db is unreachable, a
    GiraffeDBClientError is raised — there is NO silent fallback to mock.
    """
    mode = os.environ.get("GPM_CONTEXT_RETRIEVER", "mock").strip().lower()

    if mode == "mock":
        return MockContextRetriever()

    if mode == "giraffe_db":
        base_url = os.environ.get("GPM_GIRAFFE_DB_BASE_URL", "").strip()
        if not base_url:
            raise RuntimeError(
                "GPM_GIRAFFE_DB_BASE_URL is required when GPM_CONTEXT_RETRIEVER=giraffe_db"
            )

        timeout = float(os.environ.get("GPM_GIRAFFE_DB_TIMEOUT", "30.0"))
        tenant_id = os.environ.get("GPM_GIRAFFE_DB_TENANT_ID") or None
        operator_id = os.environ.get("GPM_GIRAFFE_DB_OPERATOR_ID") or None
        api_key = os.environ.get("GPM_GIRAFFE_DB_API_KEY") or None
        include_private_data = os.environ.get(
            "GPM_GIRAFFE_DB_INCLUDE_PRIVATE_DATA", "false"
        ).lower() in ("1", "true", "yes")

        client = GiraffeDBClient(
            base_url=base_url,
            timeout=timeout,
            tenant_id=tenant_id,
            operator_id=operator_id,
            api_key=api_key,
        )
        return GiraffeDBContextRetriever(
            client=client,
            default_tenant_id=tenant_id,
            include_private_data=include_private_data,
        )

    raise RuntimeError(
        f"Unsupported GPM_CONTEXT_RETRIEVER: {mode!r}. Valid values: 'mock', 'giraffe_db'"
    )
