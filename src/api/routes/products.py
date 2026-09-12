from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_credentials, get_product_service
from src.application.product_service import ProductService
from src.domain.models import ShopifyCredentials


router = APIRouter(prefix="/products", tags=["products"])


@router.get("")
async def list_products(
    credentials: Annotated[ShopifyCredentials, Depends(get_credentials)],
    service: Annotated[ProductService, Depends(get_product_service)],
    first: Annotated[
        int | None,
        Query(ge=1, description="Cantidad maxima. Si se omite, obtiene todos."),
    ] = None,
    after: str | None = None,
    search: str | None = None,
) -> dict:
    return await service.list_products(credentials, first, after, search)
