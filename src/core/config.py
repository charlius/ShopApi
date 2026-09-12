import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    shopify_api_key: str | None
    shopify_api_secret: str | None
    shopify_api_version: str
    shopify_shop: str | None
    shopify_access_token: str | None
    request_timeout: float
    max_retries: int
    retry_base_delay: float
    retry_max_delay: float


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Shopify Inventory API"),
        shopify_api_key=os.getenv("SHOPIFY_API_KEY"),
        shopify_api_secret=os.getenv("SHOPIFY_API_SECRET"),
        shopify_api_version=os.getenv("SHOPIFY_API_VERSION", "2026-07"),
        shopify_shop=os.getenv("SHOPIFY_SHOP"),
        shopify_access_token=os.getenv("SHOPIFY_ACCESS_TOKEN"),
        request_timeout=float(os.getenv("SHOPIFY_REQUEST_TIMEOUT", "15")),
        max_retries=int(os.getenv("SHOPIFY_MAX_RETRIES", "4")),
        retry_base_delay=float(os.getenv("SHOPIFY_RETRY_BASE_DELAY", "0.5")),
        retry_max_delay=float(os.getenv("SHOPIFY_RETRY_MAX_DELAY", "10")),
    )
