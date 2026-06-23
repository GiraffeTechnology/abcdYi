from __future__ import annotations

from abc import ABC, abstractmethod

from src.gpm.models.pricing_query import PricingQuery
from src.gpm.models.raw_api_response import GPMRawAPIResponse
from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample


class PricingDataAdapter(ABC):
    @abstractmethod
    def search_price_samples(
        self, query: PricingQuery
    ) -> tuple[GPMRawAPIResponse, list[GPMSupplierPriceSample]]:
        raise NotImplementedError

    @abstractmethod
    def get_offer_detail(self, offer_id: str) -> dict:
        raise NotImplementedError
