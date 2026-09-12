from typing import Annotated

from fastapi import Header, HTTPException, Request

from src.application.inventory_service import InventoryService
from src.application.oauth_service import OAuthService
from src.application.product_service import ProductService
from src.core.config import get_settings
from src.domain.models import ShopifyCredentials
from src.infrastructure.shopify.client import ShopifyClient, normalize_shop
from src.infrastructure.shopify.token_provider import ClientCredentialsTokenProvider


def get_shopify_client(request: Request) -> ShopifyClient:
    return request.app.state.shopify_client


async def get_credentials(
    request: Request,
    shop_header: Annotated[str | None, Header(alias="X-Shopify-Shop")] = None,
    token_header: Annotated[str | None, Header(alias="X-Shopify-Access-Token")] = None,
) -> ShopifyCredentials:
    settings = get_settings()
    shop = shop_header or settings.shopify_shop
    if not shop:
        raise HTTPException(status_code=401, detail="Falta la tienda de Shopify")
    shop = normalize_shop(shop)

    token = token_header or settings.shopify_access_token
    if not token:
        if not settings.shopify_api_key or not settings.shopify_api_secret:
            raise HTTPException(
                status_code=500,
                detail="SHOPIFY_API_KEY y SHOPIFY_API_SECRET no estan configurados",
            )
        provider: ClientCredentialsTokenProvider = request.app.state.token_provider
        token = await provider.get_token(
            shop,
            settings.shopify_api_key,
            settings.shopify_api_secret,
        )
    return ShopifyCredentials(shop, token)


def get_product_service(request: Request) -> ProductService:
    return ProductService(get_shopify_client(request))


def get_inventory_service(request: Request) -> InventoryService:
    return InventoryService(get_shopify_client(request))


def get_oauth_service(request: Request) -> OAuthService:
    return OAuthService(get_shopify_client(request), get_settings())
