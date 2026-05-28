"""
Cainiao-like logistics provider.
In local MVP mode: returns fixture-like mock data.
In production mode (CAINIAO_LIKE_ENABLED=true): calls the real API.
"""
from src.logistics.providers.base_provider import LogisticsProviderBase
from src.logistics.providers.cainiao_like_models import (
    CainiaoLikeTrackingEvent,
    CainiaoLikeTrackingResponse,
)
from src.logistics.providers.mock_provider import MockProvider
from src.logistics.providers.provider_config import is_cainiao_like_enabled, get_cainiao_config
from src.m_side.m_event_logger import log_m_event


class CainiaoLikeProvider(LogisticsProviderBase):
    provider_name = "cainiao_like"

    def __init__(self):
        self._mock = MockProvider()
        self._config = get_cainiao_config()
        self._api_enabled = is_cainiao_like_enabled()

    def create_or_bind_shipment(self, carrier_code, tracking_number, metadata=None) -> dict:
        return {
            "provider_shipment_id": f"CAINIAO-{tracking_number}",
            "carrier_code": carrier_code,
            "tracking_number": tracking_number,
            "status": "label_created",
            "provider": "cainiao_like",
        }

    def fetch_tracking_events(self, carrier_code, tracking_number) -> list[dict]:
        if self._api_enabled:
            return self._fetch_real_api(carrier_code, tracking_number)
        # Mock mode: return fixture-like events
        log_m_event(
            event_type="LOGISTICS_PROVIDER_API_CALLED",
            payload={
                "provider": self.provider_name,
                "mode": "mock",
                "tracking_number": tracking_number,
            },
        )
        raw_events = self._mock.fetch_tracking_events(carrier_code, tracking_number)
        return [self.normalize_event(e) for e in raw_events]

    def _fetch_real_api(self, carrier_code, tracking_number) -> list[dict]:
        # Placeholder for real Cainiao API call
        log_m_event(
            event_type="LOGISTICS_PROVIDER_API_CALLED",
            payload={"provider": self.provider_name, "mode": "real", "tracking_number": tracking_number},
        )
        try:
            raise NotImplementedError("Real Cainiao API not configured for local MVP")
        except Exception as e:
            log_m_event(
                event_type="LOGISTICS_PROVIDER_API_ERROR",
                payload={"error": str(e), "tracking_number": tracking_number},
            )
            raise

    def parse_webhook_payload(self, payload, headers=None) -> list[dict]:
        events = payload.get("events", [])
        if not events and "tracking_number" in payload:
            events = [payload]
        return [self.normalize_event(e) for e in events]

    def verify_webhook_signature(self, payload: bytes, headers: dict) -> bool:
        from src.logistics.providers.provider_config import is_production_mode
        if is_production_mode():
            secret = self._config.get("webhook_secret", "")
            if not secret:
                raise ValueError("Webhook secret not configured in production mode")
            import hmac
            import hashlib
            sig = headers.get("X-Cainiao-Signature", "")
            expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
            return hmac.compare_digest(sig, expected)
        # Local MVP: skip signature check
        log_m_event(
            event_type="LOGISTICS_WEBHOOK_SIGNATURE_VERIFIED",
            payload={"mode": "mock_bypass"},
        )
        return True

    def normalize_event(self, raw_event: dict) -> dict:
        from src.logistics.logistics_event_normalizer import normalize_raw_status
        status_text = raw_event.get("status_text") or raw_event.get("status") or ""
        status_code = raw_event.get("status_code") or ""
        normalized = normalize_raw_status(status_text or status_code)
        return {
            "provider_event_id": raw_event.get("provider_event_id"),
            "tracking_number": raw_event.get("tracking_number", ""),
            "carrier_code": raw_event.get("carrier_code"),
            "event_time": raw_event.get("event_time"),
            "status_code": status_code,
            "status_text": status_text,
            "normalized_status": normalized,
            "location": raw_event.get("location"),
            "description": raw_event.get("description"),
        }
