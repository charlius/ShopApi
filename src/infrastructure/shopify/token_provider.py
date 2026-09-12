import asyncio
import time
from dataclasses import dataclass

from src.core.errors import ShopifyError
from src.infrastructure.shopify.client import ShopifyClient


@dataclass(frozen=True, slots=True)
class CachedToken:
    value: str
    expires_at: float


class ClientCredentialsTokenProvider:
    """Obtains and caches one client-credentials token per Shopify store."""

    def __init__(self, client: ShopifyClient, refresh_margin_seconds: int = 300) -> None:
        self._client = client
        self._refresh_margin = refresh_margin_seconds
        self._cache: dict[str, CachedToken] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get_token(self, shop: str, client_id: str, client_secret: str) -> str:
        cached = self._cache.get(shop)
        if self._is_valid(cached):
            return cached.value

        lock = self._locks.setdefault(shop, asyncio.Lock())
        async with lock:
            cached = self._cache.get(shop)
            if self._is_valid(cached):
                return cached.value

            payload = await self._client.request_client_credentials_token(
                shop,
                client_id,
                client_secret,
            )
            try:
                ttl = int(payload["expires_in"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ShopifyError("expires_in invalido recibido desde Shopify") from exc

            token = str(payload["access_token"])
            self._cache[shop] = CachedToken(
                value=token,
                expires_at=time.monotonic() + ttl,
            )
            return token

    def invalidate(self, shop: str) -> None:
        self._cache.pop(shop, None)

    def _is_valid(self, token: CachedToken | None) -> bool:
        return bool(token and time.monotonic() < token.expires_at - self._refresh_margin)
