from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from .evidence_reference import GPMEvidenceReference

_CREDENTIAL_KEYS = frozenset({
    "password", "passwd", "secret", "api_key", "apikey", "token", "bearer",
    "private_key", "access_key", "credential",
})


@dataclass
class GPMContextBundle:
    """
    Packages pricing evidence and context for a single Qwen inference call.

    Data stays in this bundle; Qwen reads retrieved context at inference time
    and does not silently learn from it.
    """

    bundle_id: str
    data_mode: Literal["public", "private", "mixed", "mock"]
    requirement: dict
    supplier_quote: dict | None = None
    price_samples: list[dict] = field(default_factory=list)
    supplier_history: list[dict] = field(default_factory=list)
    public_market_notes: list[dict] = field(default_factory=list)
    private_order_history: list[dict] = field(default_factory=list)
    evidence: list[GPMEvidenceReference] = field(default_factory=list)
    tenant_id: str | None = None
    project_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def evidence_ids(self) -> set[str]:
        return {e.id for e in self.evidence}

    def get_evidence(self, evidence_id: str) -> GPMEvidenceReference | None:
        for e in self.evidence:
            if e.id == evidence_id:
                return e
        return None

    def to_prompt_payload(self, max_items: int = 20) -> dict:
        """Build a serializable payload for prompt injection.

        Includes evidence IDs, excludes credentials, deterministic for tests.
        """
        evidence_list = [
            {
                "id": e.id,
                "source_type": e.source_type,
                "source_id": e.source_id,
                "source_platform": e.source_platform,
                "title": e.title,
                "usable_for_analysis": e.usable_for_analysis,
                "payload_excerpt": _strip_credential_keys(e.payload_excerpt or {}),
            }
            for e in self.evidence[:max_items]
            if e.usable_for_analysis
        ]
        return {
            "bundle_id": self.bundle_id,
            "data_mode": self.data_mode,
            "requirement": _strip_credential_keys(self.requirement),
            "supplier_quote": _strip_credential_keys(self.supplier_quote or {}),
            "price_samples": self.price_samples[:max_items],
            "evidence": evidence_list,
            "evidence_ids": sorted(self.evidence_ids()),
        }


def _strip_credential_keys(d: dict) -> dict:
    """Return a copy of d with any credential-looking keys removed."""
    return {
        k: v
        for k, v in d.items()
        if k.lower() not in _CREDENTIAL_KEYS
    }
