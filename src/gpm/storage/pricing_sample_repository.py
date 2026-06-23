from __future__ import annotations

from src.gpm.models.raw_api_response import GPMRawAPIResponse
from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample
from src.gpm.storage.local_json_store import LocalJSONStore


class PricingSampleRepository:
    """Thin facade over LocalJSONStore. Session B may swap the backing store here."""

    def __init__(self, store: LocalJSONStore | None = None) -> None:
        self._store = store or LocalJSONStore()

    def persist_run(
        self,
        raw_response: GPMRawAPIResponse,
        samples: list[GPMSupplierPriceSample],
    ) -> tuple[str, list[str]]:
        raw_id = self._store.save_raw_response(raw_response)
        sample_ids = self._store.save_price_samples(samples)
        return raw_id, sample_ids

    def load_samples(self, ids: list[str]) -> list[GPMSupplierPriceSample]:
        return self._store.load_price_samples(ids)
