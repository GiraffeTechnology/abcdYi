from unittest.mock import MagicMock, patch

from src.gpm.audit.gpm_audit_writer import GPMAuditWriter


def test_no_op_when_no_base_url(monkeypatch):
    monkeypatch.delenv("GPM_GIRAFFE_DB_BASE_URL", raising=False)
    GPMAuditWriter().write_execution_event({"event_type": "test"})  # must not raise


def test_best_effort_swallows_connection_errors(monkeypatch):
    monkeypatch.setenv("GPM_GIRAFFE_DB_BASE_URL", "http://localhost:19999")
    GPMAuditWriter().write_execution_event({"event_type": "test"})  # must not raise


def test_api_key_not_in_logged_payload(monkeypatch):
    monkeypatch.setenv("GPM_GIRAFFE_DB_BASE_URL", "http://localhost:19999")
    monkeypatch.setenv("GPM_GIRAFFE_DB_API_KEY", "super-secret-key")

    with patch("httpx.Client") as mock_cls:
        instance = MagicMock()
        instance.__enter__ = lambda s: instance
        instance.__exit__ = MagicMock(return_value=False)
        instance.post.side_effect = Exception("mock fail")
        mock_cls.return_value = instance

        GPMAuditWriter().write_execution_event({"event_type": "test"})

    posted_json = instance.post.call_args
    # key must not appear in the json payload body
    assert "super-secret-key" not in str(posted_json.kwargs.get("json", {}))
