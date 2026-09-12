import hashlib
import hmac
from urllib.parse import urlencode

from src.core.config import Settings
from src.core.errors import ShopifyError
from src.infrastructure.shopify.client import ShopifyClient, normalize_shop


class OAuthService:
    def __init__(self, client: ShopifyClient, settings: Settings) -> None:
        self._client = client
        self._settings = settings

    async def complete_installation(self, query_params: dict[str, str]) -> dict:
        params = query_params.copy()
        received_hmac = params.pop("hmac", None)
        shop = normalize_shop(params.get("shop", ""))
        code = params.get("code")
        if not received_hmac or not code:
            raise ShopifyError("El callback OAuth debe incluir hmac, shop y code", status_code=400)
        if not self._settings.shopify_api_secret:
            raise ShopifyError("SHOPIFY_API_SECRET no esta configurado", status_code=500)
        message = urlencode(sorted(params.items()))
        expected = hmac.new(self._settings.shopify_api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(received_hmac, expected):
            raise ShopifyError("HMAC de Shopify no valido", status_code=401)
        token = await self._client.exchange_oauth_code(shop, code)
        return {"shop": shop, **token}
