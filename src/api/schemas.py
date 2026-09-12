from uuid import uuid4

from pydantic import BaseModel, Field


class StockUpdateRequest(BaseModel):
    inventory_item_id: str = Field(examples=["gid://shopify/InventoryItem/30322695"])
    location_id: str = Field(examples=["gid://shopify/Location/124656943"])
    quantity: int = Field(ge=0)
    change_from_quantity: int | None = Field(default=None, ge=0)
    reference_document_uri: str = "shop-api://inventory/correction"
    idempotency_key: str = Field(default_factory=lambda: str(uuid4()))
