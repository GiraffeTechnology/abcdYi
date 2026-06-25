from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)


class GPMAuditWriter:
    """Best-effort writeback of GPM execution events to giraffe-db.

    All failures are silently swallowed — audit writeback must never affect
    the API response. API keys are passed in headers only and never logged.
    """

    def write_execution_event(self, payload: dict) -> None:
        base_url = os.getenv("GPM_GIRAFFE_DB_BASE_URL", "").rstrip("/")
        if not base_url:
            return
        api_key = os.getenv("GPM_GIRAFFE_DB_API_KEY", "")
        try:
            headers: dict[str, str] = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            with httpx.Client(base_url=base_url, timeout=8.0) as client:
                client.post("/execution-events", json=payload, headers=headers)
        except Exception:
            logger.debug("GPM audit writeback to giraffe-db failed (best-effort, no-op).")
