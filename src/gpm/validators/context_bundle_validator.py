from __future__ import annotations

from typing import Any

from src.gpm.context.gpm_context_bundle import GPMContextBundle

_VALID_DATA_MODES = frozenset({"public", "private", "mixed", "mock"})

_CREDENTIAL_KEYS = frozenset({
    "password", "passwd", "secret", "api_key", "apikey", "token", "bearer",
    "private_key", "access_key", "credential",
})


class ContextBundleValidationError(ValueError):
    pass


def validate_context_bundle(bundle: GPMContextBundle) -> None:
    """Validate a GPMContextBundle.

    Raises ContextBundleValidationError on any violation.
    """
    if not bundle.bundle_id or not bundle.bundle_id.strip():
        raise ContextBundleValidationError("bundle_id must not be empty.")

    if bundle.data_mode not in _VALID_DATA_MODES:
        raise ContextBundleValidationError(
            f"data_mode must be one of {sorted(_VALID_DATA_MODES)}, got {bundle.data_mode!r}."
        )

    evidence_ids = [e.id for e in bundle.evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        seen: set[str] = set()
        dupes = [eid for eid in evidence_ids if eid in seen or seen.add(eid)]
        raise ContextBundleValidationError(
            f"Evidence IDs must be unique. Duplicates found: {dupes}"
        )

    if not bundle.requirement:
        raise ContextBundleValidationError("requirement must not be empty.")

    cred_findings = _check_credential_keys(bundle.requirement, "requirement")
    if bundle.supplier_quote:
        cred_findings.extend(_check_credential_keys(bundle.supplier_quote, "supplier_quote"))
    for ev in bundle.evidence:
        if ev.payload_excerpt:
            cred_findings.extend(
                _check_credential_keys(ev.payload_excerpt, f"evidence[{ev.id}].payload_excerpt")
            )
    if cred_findings:
        raise ContextBundleValidationError(
            f"Context bundle contains credential-looking field(s): {cred_findings}"
        )


def _check_credential_keys(obj: Any, path: str = "") -> list[str]:
    findings: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            k_lower = k.lower() if isinstance(k, str) else ""
            if k_lower in _CREDENTIAL_KEYS:
                findings.append(f"{path}.{k}" if path else k)
            findings.extend(_check_credential_keys(v, path=f"{path}.{k}" if path else k))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            findings.extend(_check_credential_keys(item, path=f"{path}[{i}]"))
    return findings
