"""Logistics provider configuration — reads from environment variables."""
import os


def get_provider_name() -> str:
    return os.environ.get("LOGISTICS_PROVIDER", "mock").lower()


def is_api_enabled() -> bool:
    return os.environ.get("LOGISTICS_API_ENABLED", "false").lower() == "true"


def is_cainiao_like_enabled() -> bool:
    return os.environ.get("CAINIAO_LIKE_ENABLED", "false").lower() == "true"


def get_cainiao_config() -> dict:
    return {
        "api_base_url": os.environ.get("CAINIAO_LIKE_API_BASE_URL", ""),
        "app_key": os.environ.get("CAINIAO_LIKE_APP_KEY", ""),
        "app_secret": os.environ.get("CAINIAO_LIKE_APP_SECRET", ""),
        "access_token": os.environ.get("CAINIAO_LIKE_ACCESS_TOKEN", ""),
        "signing_method": os.environ.get("CAINIAO_LIKE_SIGNING_METHOD", "hmac_sha256"),
        "timeout_seconds": int(os.environ.get("CAINIAO_LIKE_TIMEOUT_SECONDS", "10")),
        "max_retries": int(os.environ.get("CAINIAO_LIKE_MAX_RETRIES", "3")),
        "webhook_secret": os.environ.get("CAINIAO_LIKE_WEBHOOK_SECRET", ""),
    }


def is_production_mode() -> bool:
    return os.environ.get("GIRAFFE_ENV", "local").lower() == "production"
