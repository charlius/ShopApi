from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import get_credentials, get_inventory_service
from src.api.schemas import StockUpdateRequest
from src.application.inventory_service import InventoryService
from src.domain.models import ShopifyCredentials, StockUpdate


router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.put("/stock")
async def set_stock(
    body: StockUpdateRequest,
    credentials: Annotated[ShopifyCredentials, Depends(get_credentials)],
    service: Annotated[InventoryService, Depends(get_inventory_service)],
) -> dict:
    update = StockUpdate(**body.model_dump())
    return await service.set_stock(credentials, update)
