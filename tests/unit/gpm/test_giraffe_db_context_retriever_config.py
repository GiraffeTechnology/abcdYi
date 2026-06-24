"""Unit tests for build_context_retriever_from_env factory."""
from __future__ import annotations

import pytest

from src.gpm.context.retrievers.retriever_config import build_context_retriever_from_env
from src.gpm.context.retrievers.mock_context_retriever import MockContextRetriever
from src.gpm.context.retrievers.giraffe_db_context_retriever import GiraffeDBContextRetriever


class TestBuildContextRetrieverFromEnv:
    def test_default_returns_mock_retriever(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GPM_CONTEXT_RETRIEVER", raising=False)
        retriever = build_context_retriever_from_env()
        assert isinstance(retriever, MockContextRetriever)

    def test_explicit_mock_returns_mock_retriever(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GPM_CONTEXT_RETRIEVER", "mock")
        retriever = build_context_retriever_from_env()
        assert isinstance(retriever, MockContextRetriever)

    def test_giraffe_db_without_url_raises_runtime_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GPM_CONTEXT_RETRIEVER", "giraffe_db")
        monkeypatch.delenv("GPM_GIRAFFE_DB_BASE_URL", raising=False)
        with pytest.raises(RuntimeError, match="GPM_GIRAFFE_DB_BASE_URL"):
            build_context_retriever_from_env()

    def test_giraffe_db_with_url_returns_giraffe_db_retriever(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GPM_CONTEXT_RETRIEVER", "giraffe_db")
        monkeypatch.setenv("GPM_GIRAFFE_DB_BASE_URL", "http://localhost:8001")
        retriever = build_context_retriever_from_env()
        assert isinstance(retriever, GiraffeDBContextRetriever)

    def test_unknown_mode_raises_runtime_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GPM_CONTEXT_RETRIEVER", "postgres_direct")
        with pytest.raises(RuntimeError, match="Unsupported GPM_CONTEXT_RETRIEVER"):
            build_context_retriever_from_env()

    def test_giraffe_db_reads_optional_env_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GPM_CONTEXT_RETRIEVER", "giraffe_db")
        monkeypatch.setenv("GPM_GIRAFFE_DB_BASE_URL", "http://localhost:8001")
        monkeypatch.setenv("GPM_GIRAFFE_DB_TIMEOUT", "15.0")
        monkeypatch.setenv("GPM_GIRAFFE_DB_TENANT_ID", "tenant_abc")
        monkeypatch.setenv("GPM_GIRAFFE_DB_INCLUDE_PRIVATE_DATA", "true")
        # Should not raise; extra env vars are consumed silently
        retriever = build_context_retriever_from_env()
        assert isinstance(retriever, GiraffeDBContextRetriever)
