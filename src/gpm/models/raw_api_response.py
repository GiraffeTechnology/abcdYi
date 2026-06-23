from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class GPMRawAPIResponse:
    id: str
    source_platform: str
    api_endpoint: str
    query_keyword: str
    query_payload: dict
    response_payload: dict
    response_hash: str
    captured_at: datetime
    request_status: str
    api_account_id: str | None = None
    error_message: str | None = None
