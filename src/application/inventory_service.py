from typing import Any

from src.core.errors import ShopifyError
from src.domain.models import ShopifyCredentials, StockUpdate
from src.infrastructure.shopify.client import ShopifyClient


SET_STOCK_MUTATION = """
mutation InventorySet($input: InventorySetQuantitiesInput!, $idempotencyKey: String!) {
  inventorySetQuantities(input: $input) @idempotent(key: $idempotencyKey) {
    inventoryAdjustmentGroup {
      createdAt reason referenceDocumentUri
      changes { name delta quantityAfterChange }
    }
    userErrors { code field message }
  }
}
"""


class InventoryService:
    def __init__(self, client: ShopifyClient) -> None:
        self._client = client

    async def set_stock(self, credentials: ShopifyCredentials, update: StockUpdate) -> dict[str, Any]:
        quantity = {
            "inventoryItemId": update.inventory_item_id,
            "locationId": update.location_id,
            "quantity": update.quantity,
        }
        if update.change_from_quantity is not None:
            quantity["changeFromQuantity"] = update.change_from_quantity

        data = await self._client.graphql(
            credentials,
            SET_STOCK_MUTATION,
            {
                "idempotencyKey": update.idempotency_key,
                "input": {
                    "name": "available",
                    "reason": "correction",
                    "referenceDocumentUri": update.reference_document_uri,
                    "ignoreCompareQuantity": update.change_from_quantity is None,
                    "quantities": [quantity],
                },
            },
        )
        result = data["inventorySetQuantities"]
        if result["userErrors"]:
            raise ShopifyError("No se pudo actualizar el stock", status_code=422, details=result["userErrors"])
        return result["inventoryAdjustmentGroup"]
