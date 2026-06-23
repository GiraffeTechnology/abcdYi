from __future__ import annotations

from src.gpm.context.gpm_context_bundle import GPMContextBundle

_VALID_DATA_MODES = frozenset({"public", "private", "mixed", "mock"})

_CREDENTIAL_KEYS = frozenset({
    "password", "secret", "token", "api_key", "apikey", "credential",
    "private_key", "access_key", "auth", "bearer",
})


class ContextBundleValidationError(ValueError):
    pass


class ContextBundleValidator:
    """Validate a GPMContextBundle before it is sent to Qwen."""

    def validate(self, bundle: GPMContextBundle) -> None:
        if not bundle.bundle_id:
            raise ContextBundleValidationError("bundle_id must not be empty.")

        if bundle.data_mode not in _VALID_DATA_MODES:
            raise ContextBundleValidationError(
                f"data_mode must be one of {sorted(_VALID_DATA_MODES)}, got {bundle.data_mode!r}."
            )

        ids = [e.id for e in bundle.evidence]
        if len(ids) != len(set(ids)):
            duplicates = [eid for eid in set(ids) if ids.count(eid) > 1]
            raise ContextBundleValidationError(
                f"Evidence IDs must be unique. Duplicates found: {duplicates}"
            )

        if not bundle.requirement:
            raise ContextBundleValidationError("requirement must not be empty.")

        self._check_no_credentials(bundle)

    def _check_no_credentials(self, bundle: GPMContextBundle) -> None:
        self._check_dict_keys(bundle.requirement, "requirement")
        if bundle.supplier_quote:
            self._check_dict_keys(bundle.supplier_quote, "supplier_quote")
        for i, e in enumerate(bundle.evidence):
            if e.payload_excerpt:
                self._check_dict_keys(e.payload_excerpt, f"evidence[{i}].payload_excerpt")

    def _check_dict_keys(self, d: dict, location: str) -> None:
        for key in d:
            if key.lower() in _CREDENTIAL_KEYS:
                raise ContextBundleValidationError(
                    f"Credential-looking field {key!r} found in {location}. "
                    "Context bundles must not contain credentials."
                )
