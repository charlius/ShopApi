from typing import Any

from src.core.errors import ShopifyError
from src.domain.models import ShopifyCredentials
from src.infrastructure.shopify.client import ShopifyClient


ORDER_FIELDS = """
fragment OrderFields on Order {
  id
  legacyResourceId
  name
  createdAt
  cancelledAt
  displayFinancialStatus
  displayFulfillmentStatus
  paymentGatewayNames
  customer { displayName }
  totalPriceSet { shopMoney { amount currencyCode } }
  fulfillments(first: 20) {
    displayStatus
    deliveredAt
    estimatedDeliveryAt
    trackingInfo(first: 10) { company number url }
  }
}
"""

ORDERS_QUERY = """
query Orders($first: Int!, $after: String, $query: String) {
  orders(first: $first, after: $after, query: $query, sortKey: CREATED_AT, reverse: true) {
    nodes { ...OrderFields }
    pageInfo { hasNextPage endCursor }
  }
}
""" + ORDER_FIELDS

ORDER_QUERY = """
query Order($id: ID!) {
  order(id: $id) {
    ...OrderFields
    email
    phone
    shippingAddress {
      name
      address1
      address2
      city
      province
      country
      zip
      phone
    }
    lineItems(first: 100) {
      nodes {
        id
        name
        sku
        quantity
        image { url }
        originalUnitPriceSet { shopMoney { amount currencyCode } }
        discountedTotalSet { shopMoney { amount currencyCode } }
      }
    }
  }
}
""" + ORDER_FIELDS


class OrderService:
    def __init__(self, client: ShopifyClient) -> None:
        self._client = client

    async def list_orders(
        self,
        credentials: ShopifyCredentials,
        first: int,
        after: str | None,
        search: str | None,
        status: str,
    ) -> dict[str, Any]:
        data = await self._client.graphql(
            credentials,
            ORDERS_QUERY,
            {"first": first, "after": after, "query": search or None},
        )
        connection = data["orders"]
        orders = [self._serialize_summary(order) for order in connection["nodes"]]

        if status != "todos":
            orders = [order for order in orders if order["status"] == status]

        return {
            "nodes": orders,
            "count": len(orders),
            "pageInfo": connection["pageInfo"],
        }

    async def get_order(
        self,
        credentials: ShopifyCredentials,
        order_id: int,
    ) -> dict[str, Any]:
        data = await self._client.graphql(
            credentials,
            ORDER_QUERY,
            {"id": f"gid://shopify/Order/{order_id}"},
        )
        order = data.get("order")
        if not order:
            raise ShopifyError("Pedido no encontrado", status_code=404)

        result = self._serialize_summary(order)
        result.update(
            {
                "email": order.get("email"),
                "phone": order.get("phone"),
                "paymentMethods": order.get("paymentGatewayNames") or [],
                "shippingAddress": order.get("shippingAddress"),
                "shipping": self._serialize_shipping(order.get("fulfillments") or []),
                "items": [self._serialize_item(item) for item in order["lineItems"]["nodes"]],
            }
        )
        return result

    @classmethod
    def _serialize_summary(cls, order: dict[str, Any]) -> dict[str, Any]:
        money = order["totalPriceSet"]["shopMoney"]
        customer = order.get("customer")
        return {
            "id": int(order["legacyResourceId"]),
            "shopifyId": order["id"],
            "number": order["name"],
            "createdAt": order["createdAt"],
            "customer": customer.get("displayName") if customer else "Cliente invitado",
            "total": money["amount"],
            "currency": money["currencyCode"],
            "status": cls._status(order),
            "financialStatus": order.get("displayFinancialStatus"),
            "fulfillmentStatus": order.get("displayFulfillmentStatus"),
        }

    @staticmethod
    def _status(order: dict[str, Any]) -> str:
        if order.get("cancelledAt"):
            return "cancelado"

        fulfillment_statuses = {
            fulfillment.get("displayStatus")
            for fulfillment in order.get("fulfillments") or []
        }
        if "DELIVERED" in fulfillment_statuses:
            return "entregado"
        if fulfillment_statuses.intersection(
            {"CARRIER_PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "FULFILLED", "MARKED_AS_FULFILLED"}
        ):
            return "enviado"
        if order.get("displayFulfillmentStatus") in {
            "IN_PROGRESS",
            "ON_HOLD",
            "PARTIALLY_FULFILLED",
            "PENDING_FULFILLMENT",
            "SCHEDULED",
        }:
            return "preparando"
        if order.get("displayFinancialStatus") == "PAID":
            return "pagado"
        return "pendiente"

    @staticmethod
    def _serialize_shipping(fulfillments: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not fulfillments:
            return None

        latest = fulfillments[-1]
        return {
            "status": latest.get("displayStatus"),
            "deliveredAt": latest.get("deliveredAt"),
            "estimatedDeliveryAt": latest.get("estimatedDeliveryAt"),
            "tracking": latest.get("trackingInfo") or [],
        }

    @staticmethod
    def _serialize_item(item: dict[str, Any]) -> dict[str, Any]:
        unit_price = item["originalUnitPriceSet"]["shopMoney"]
        total = item["discountedTotalSet"]["shopMoney"]
        image = item.get("image")
        return {
            "id": item["id"],
            "name": item["name"],
            "sku": item.get("sku"),
            "quantity": item["quantity"],
            "image": image.get("url") if image else None,
            "unitPrice": unit_price["amount"],
            "total": total["amount"],
            "currency": total["currencyCode"],
        }
