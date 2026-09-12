import unittest

from src.application.order_service import OrderService
from src.core.errors import ShopifyError
from src.domain.models import ShopifyCredentials


def sample_order(**changes):
    order = {
        "id": "gid://shopify/Order/1045",
        "legacyResourceId": "1045",
        "name": "#1045",
        "createdAt": "2026-09-08T12:00:00Z",
        "cancelledAt": None,
        "displayFinancialStatus": "PAID",
        "displayFulfillmentStatus": "UNFULFILLED",
        "paymentGatewayNames": ["shopify_payments"],
        "customer": {"displayName": "Cliente Shopify"},
        "totalPriceSet": {"shopMoney": {"amount": "12000.00", "currencyCode": "CLP"}},
        "fulfillments": [],
    }
    order.update(changes)
    return order


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def graphql(self, credentials, query, variables):
        self.calls.append((credentials, query, variables))
        return self.responses.pop(0)


class OrderServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_list_orders_serializes_and_filters_status(self):
        client = FakeClient(
            [
                {
                    "orders": {
                        "nodes": [sample_order(), sample_order(legacyResourceId="1044", name="#1044", cancelledAt="2026-09-07T12:00:00Z")],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            ]
        )
        service = OrderService(client)

        result = await service.list_orders(
            ShopifyCredentials("example.myshopify.com", "token"),
            50,
            None,
            "1045",
            "pagado",
        )

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["nodes"][0]["number"], "#1045")
        self.assertEqual(result["nodes"][0]["customer"], "Cliente Shopify")
        self.assertEqual(client.calls[0][2]["query"], "1045")

    async def test_get_order_includes_items_and_shipping(self):
        order = sample_order(
            displayFulfillmentStatus="FULFILLED",
            fulfillments=[
                {
                    "displayStatus": "DELIVERED",
                    "deliveredAt": "2026-09-10T12:00:00Z",
                    "estimatedDeliveryAt": None,
                    "trackingInfo": [{"company": "Chilexpress", "number": "ABC", "url": "https://example.com/ABC"}],
                }
            ],
        )
        order.update(
            {
                "email": "cliente@example.com",
                "phone": None,
                "shippingAddress": {"city": "Santiago"},
                "lineItems": {
                    "nodes": [
                        {
                            "id": "gid://shopify/LineItem/1",
                            "name": "Producto",
                            "sku": "SKU-1",
                            "quantity": 2,
                            "image": None,
                            "originalUnitPriceSet": {"shopMoney": {"amount": "6000.00", "currencyCode": "CLP"}},
                            "discountedTotalSet": {"shopMoney": {"amount": "12000.00", "currencyCode": "CLP"}},
                        }
                    ]
                },
            }
        )
        client = FakeClient([{"order": order}])
        service = OrderService(client)

        result = await service.get_order(
            ShopifyCredentials("example.myshopify.com", "token"), 1045
        )

        self.assertEqual(result["status"], "entregado")
        self.assertEqual(result["items"][0]["quantity"], 2)
        self.assertEqual(result["shipping"]["tracking"][0]["number"], "ABC")
        self.assertEqual(client.calls[0][2]["id"], "gid://shopify/Order/1045")

    async def test_get_order_returns_404_when_missing(self):
        service = OrderService(FakeClient([{"order": None}]))

        with self.assertRaises(ShopifyError) as context:
            await service.get_order(
                ShopifyCredentials("example.myshopify.com", "token"), 999
            )

        self.assertEqual(context.exception.status_code, 404)


if __name__ == "__main__":
    unittest.main()
