from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from src.api.dependencies import get_credentials, get_order_service
from src.application.order_service import OrderService
from src.domain.models import ShopifyCredentials


OrderStatus = Literal[
    "todos",
    "pagado",
    "pendiente",
    "preparando",
    "enviado",
    "entregado",
    "cancelado",
]

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("")
async def list_orders(
    credentials: Annotated[ShopifyCredentials, Depends(get_credentials)],
    service: Annotated[OrderService, Depends(get_order_service)],
    first: Annotated[int, Query(ge=1, le=100)] = 50,
    after: str | None = None,
    search: Annotated[str | None, Query(max_length=255)] = None,
    status: OrderStatus = "todos",
) -> dict:
    return await service.list_orders(credentials, first, after, search, status)


@router.get("/{order_id}")
async def get_order(
    order_id: int,
    credentials: Annotated[ShopifyCredentials, Depends(get_credentials)],
    service: Annotated[OrderService, Depends(get_order_service)],
) -> dict:
    return await service.get_order(credentials, order_id)
