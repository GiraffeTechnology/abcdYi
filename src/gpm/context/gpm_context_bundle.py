from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from src.gpm.context.evidence_reference import GPMEvidenceReference

_CREDENTIAL_KEYS = frozenset({
    # Base set
    "password", "passwd", "secret", "token", "api_key", "apikey", "credential",
    "private_key", "access_key", "auth", "bearer", "authorization", "cookie",
    "session",
    # Extended variants
    "access_token", "refresh_token", "api_token", "authorization_header",
    "id_token", "client_secret", "jwt", "x_api_key",
})


def _has_credential_keys(d: dict) -> bool:
    for key in d:
        if key.lower() in _CREDENTIAL_KEYS:
            return True
    return False


def _scrub_credentials(d: Any) -> Any:
    """Recursively remove credential keys from dicts and lists."""
    if isinstance(d, dict):
        return {k: _scrub_credentials(v) for k, v in d.items() if k.lower() not in _CREDENTIAL_KEYS}
    if isinstance(d, list):
        return [_scrub_credentials(item) for item in d]
    return d


@dataclass
class GPMContextBundle:
    bundle_id: str
    data_mode: Literal["public", "private", "mixed", "mock"]
    requirement: dict
    evidence: list[GPMEvidenceReference] = field(default_factory=list)
    tenant_id: str | None = None
    project_id: str | None = None
    supplier_quote: dict | None = None
    price_samples: list[dict] = field(default_factory=list)
    supplier_history: list[dict] = field(default_factory=list)
    public_market_notes: list[dict] = field(default_factory=list)
    private_order_history: list[dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        data_mode: Literal["public", "private", "mixed", "mock"],
        requirement: dict,
        **kwargs: object,
    ) -> "GPMContextBundle":
        return cls(
            bundle_id=str(uuid.uuid4()),
            data_mode=data_mode,
            requirement=requirement,
            **kwargs,
        )

    def evidence_ids(self) -> set[str]:
        return {e.id for e in self.evidence}

    def get_evidence(self, evidence_id: str) -> GPMEvidenceReference | None:
        for e in self.evidence:
            if e.id == evidence_id:
                return e
        return None

    def to_prompt_payload(self, max_items: int = 20) -> dict:
        usable = [e for e in self.evidence if e.usable_for_analysis]
        selected = usable[:max_items]

        evidence_list = []
        for e in selected:
            entry: dict = {
                "id": e.id,
                "source_type": e.source_type,
                "source_platform": e.source_platform,
                "title": e.title,
                "observed_at": e.observed_at.isoformat() if e.observed_at else None,
            }
            if e.payload_excerpt:
                entry["payload_excerpt"] = _scrub_credentials(e.payload_excerpt)
            evidence_list.append(entry)

        return {
            "bundle_id": self.bundle_id,
            "data_mode": self.data_mode,
            "requirement": self.requirement,
            "evidence_ids": [e.id for e in selected],
            "evidence": evidence_list,
            "supplier_quote": self.supplier_quote,
            "sample_count": len(self.price_samples),
        }
