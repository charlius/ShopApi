from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.router import api_router
from src.core.config import get_settings
from src.core.errors import register_exception_handlers
from src.infrastructure.shopify.client import ShopifyClient
from src.infrastructure.shopify.token_provider import ClientCredentialsTokenProvider


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.shopify_client = ShopifyClient(settings)
    app.state.token_provider = ClientCredentialsTokenProvider(app.state.shopify_client)
    yield
    await app.state.shopify_client.close()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
