from typing import Any

from src.domain.models import ShopifyCredentials
from src.infrastructure.shopify.client import ShopifyClient


PRODUCTS_QUERY = """
query Products($first: Int!, $after: String, $query: String) {
  products(first: $first, after: $after, query: $query) {
    nodes {
      id
      title
      handle
      description
      vendor
      productType
      tags
      featuredMedia { preview { image { url } } }
      priceRangeV2 { minVariantPrice { amount currencyCode } }
      compareAtPriceRange { minVariantCompareAtPrice { amount currencyCode } }
      variants(first: 100) {
        nodes { ...VariantFields }
        pageInfo { hasNextPage endCursor }
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}

fragment VariantFields on ProductVariant {
  id
  sku
  title
  inventoryQuantity
  price
  availableForSale
  inventoryItem { measurement { weight { value unit } } }
}
"""

VARIANTS_QUERY = """
query ProductVariants($id: ID!, $first: Int!, $after: String) {
  product(id: $id) {
    variants(first: $first, after: $after) {
      nodes { ...VariantFields }
      pageInfo { hasNextPage endCursor }
    }
  }
}

fragment VariantFields on ProductVariant {
  id
  sku
  title
  inventoryQuantity
  price
  availableForSale
  inventoryItem { measurement { weight { value unit } } }
}
"""


class ProductService:
    def __init__(self, client: ShopifyClient) -> None:
        self._client = client

    async def list_products(
        self,
        credentials: ShopifyCredentials,
        limit: int | None,
        after: str | None,
        search: str | None,
    ) -> dict[str, Any]:
        products: list[dict[str, Any]] = []
        cursor = after
        has_next_page = True

        while has_next_page and (limit is None or len(products) < limit):
            page_size = min(100, limit - len(products)) if limit is not None else 100
            data = await self._client.graphql(
                credentials,
                PRODUCTS_QUERY,
                {"first": page_size, "after": cursor, "query": search},
            )
            page = data["products"]
            for product in page["nodes"]:
                variants = await self._all_variants(credentials, product)
                products.append(self._serialize_product(product, variants))
            page_info = page["pageInfo"]
            has_next_page = page_info["hasNextPage"]
            next_cursor = page_info["endCursor"]

            if has_next_page and (not next_cursor or next_cursor == cursor):
                break
            cursor = next_cursor

        return {
            "nodes": products,
            "count": len(products),
            "pageInfo": {
                "hasNextPage": has_next_page,
                "endCursor": cursor,
            },
        }

    async def _all_variants(
        self,
        credentials: ShopifyCredentials,
        product: dict[str, Any],
    ) -> list[dict[str, Any]]:
        connection = product["variants"]
        variants = list(connection["nodes"])
        page_info = connection["pageInfo"]
        cursor = page_info["endCursor"]

        while page_info["hasNextPage"] and cursor:
            data = await self._client.graphql(
                credentials,
                VARIANTS_QUERY,
                {"id": product["id"], "first": 100, "after": cursor},
            )
            connection = data["product"]["variants"]
            variants.extend(connection["nodes"])
            page_info = connection["pageInfo"]
            next_cursor = page_info["endCursor"]
            if next_cursor == cursor:
                break
            cursor = next_cursor
        return variants

    @staticmethod
    def _serialize_product(
        product: dict[str, Any],
        variants: list[dict[str, Any]],
    ) -> dict[str, Any]:
        price = product["priceRangeV2"]["minVariantPrice"]
        compare_at_range = product.get("compareAtPriceRange")
        compare_at = (
            compare_at_range.get("minVariantCompareAtPrice")
            if compare_at_range
            else None
        )
        image = (
            product.get("featuredMedia", {}).get("preview", {}).get("image")
            if product.get("featuredMedia")
            else None
        )

        return {
            "id": product["id"],
            "title": product["title"],
            "handle": product["handle"],
            "description": product["description"],
            "image": image.get("url") if image else None,
            "price": price["amount"],
            "compareAtPrice": compare_at["amount"] if compare_at else None,
            "currency": price["currencyCode"],
            "available": any(variant["availableForSale"] for variant in variants),
            "vendor": product["vendor"],
            "productType": product["productType"],
            "tags": product["tags"],
            "variants": [ProductService._serialize_variant(variant) for variant in variants],
        }

    @staticmethod
    def _serialize_variant(variant: dict[str, Any]) -> dict[str, Any]:
        weight = variant["inventoryItem"]["measurement"].get("weight")
        return {
            "id": variant["id"],
            "sku": variant.get("sku"),
            "title": variant["title"],
            "quantity": variant.get("inventoryQuantity") or 0,
            "price": variant["price"],
            "weight": weight["value"] if weight else None,
            "weightUnit": weight["unit"] if weight else None,
            "available": variant["availableForSale"],
        }
