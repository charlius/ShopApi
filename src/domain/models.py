from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ShopifyCredentials:
    shop: str
    access_token: str


@dataclass(frozen=True, slots=True)
class StockUpdate:
    inventory_item_id: str
    location_id: str
    quantity: int
    change_from_quantity: int | None
    reference_document_uri: str
    idempotency_key: str
