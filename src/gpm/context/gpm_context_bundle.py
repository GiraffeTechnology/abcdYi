from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

from src.gpm.context.evidence_reference import GPMEvidenceReference

_CREDENTIAL_KEYS = frozenset({
    "password", "secret", "token", "api_key", "apikey", "credential",
    "private_key", "access_key", "auth", "bearer",
})


def _has_credential_keys(d: dict) -> bool:
    for key in d:
        if key.lower() in _CREDENTIAL_KEYS:
            return True
    return False


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
                # Drop credential-looking keys from excerpts
                safe = {k: v for k, v in e.payload_excerpt.items() if k.lower() not in _CREDENTIAL_KEYS}
                entry["payload_excerpt"] = safe
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
