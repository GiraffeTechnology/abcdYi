from __future__ import annotations

import os

from src.gpm.adapters.pricing_data_adapter import PricingDataAdapter
from src.gpm.models.pricing_query import PricingQuery
from src.gpm.models.raw_api_response import GPMRawAPIResponse
from src.gpm.models.supplier_price_sample import GPMSupplierPriceSample


class Real1688PricingAdapter(PricingDataAdapter):
    """Stub adapter for the real 1688 API.

    Requires credentials via environment variables.
    Live mode is off by default; set GPM_ENABLE_LIVE_1688_TESTS=true to enable.
    """

    ENV_ENABLE_LIVE = "GPM_ENABLE_LIVE_1688_TESTS"
    ENV_APP_KEY = "GPM_1688_APP_KEY"
    ENV_APP_SECRET = "GPM_1688_APP_SECRET"
    ENV_ACCESS_TOKEN = "GPM_1688_ACCESS_TOKEN"
    ENV_API_BASE_URL = "GPM_1688_API_BASE_URL"

    def __init__(self) -> None:
        self._live_mode = os.environ.get(self.ENV_ENABLE_LIVE, "").lower() == "true"

    def search_price_samples(
        self, query: PricingQuery
    ) -> tuple[GPMRawAPIResponse, list[GPMSupplierPriceSample]]:
        self._require_live_mode()
        self._assert_credentials()
        raise NotImplementedError("Live 1688 API integration not yet implemented.")

    def get_offer_detail(self, offer_id: str) -> dict:
        self._require_live_mode()
        self._assert_credentials()
        raise NotImplementedError("Live 1688 API integration not yet implemented.")

    def _require_live_mode(self) -> None:
        if not self._live_mode:
            raise RuntimeError(
                "Real1688PricingAdapter is a stub. "
                "Set GPM_ENABLE_LIVE_1688_TESTS=true and provide credentials to use live mode."
            )

    def _assert_credentials(self) -> None:
        missing = [
            key
            for key in (self.ENV_APP_KEY, self.ENV_ACCESS_TOKEN, self.ENV_API_BASE_URL)
            if not os.environ.get(key)
        ]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables for live 1688 API: {', '.join(missing)}. "
                "Do not hardcode credentials. Set them in your environment."
            )
