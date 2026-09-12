import asyncio
import random
import re
from typing import Any

import httpx

from src.core.config import Settings
from src.core.errors import ShopifyError
from src.domain.models import ShopifyCredentials


SHOP_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]*\.myshopify\.com")


def normalize_shop(shop: str) -> str:
    normalized = shop.lower().removeprefix("https://").removeprefix("http://").rstrip("/")
    if "." not in normalized:
        normalized = f"{normalized}.myshopify.com"
    if not SHOP_PATTERN.fullmatch(normalized):
        raise ShopifyError("Dominio de Shopify no valido", status_code=400)
    return normalized


class ShopifyClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._http = httpx.AsyncClient(timeout=settings.request_timeout)

    async def close(self) -> None:
        await self._http.aclose()

    async def graphql(self, credentials: ShopifyCredentials, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"https://{credentials.shop}/admin/api/{self._settings.shopify_api_version}/graphql.json"
        last_error: object = None
        payload: dict[str, Any] | None = None

        for attempt in range(self._settings.max_retries + 1):
            try:
                response = await self._http.post(
                    url,
                    headers={"X-Shopify-Access-Token": credentials.access_token},
                    json={"query": query, "variables": variables or {}},
                )
            except httpx.RequestError as exc:
                last_error = str(exc)
                if attempt >= self._settings.max_retries:
                    break
                await asyncio.sleep(self._backoff(attempt))
                continue

            if response.status_code in {429, 500, 502, 503, 504}:
                last_error = self._response_details(response)
                if attempt >= self._settings.max_retries:
                    break
                await asyncio.sleep(self._http_retry_delay(response, attempt))
                continue

            if response.is_error:
                raise ShopifyError(
                    "Shopify rechazo la solicitud",
                    details={"status": response.status_code, "response": self._response_details(response)},
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise ShopifyError("Shopify devolvio una respuesta JSON invalida") from exc

            errors = payload.get("errors") or []
            retryable_codes = {"THROTTLED", "INTERNAL_SERVER_ERROR"}
            codes = {error.get("extensions", {}).get("code") for error in errors}
            if errors and codes.intersection(retryable_codes):
                last_error = errors
                if attempt >= self._settings.max_retries:
                    break
                await asyncio.sleep(self._graphql_retry_delay(payload, attempt))
                continue
            if errors:
                raise ShopifyError("Shopify devolvio errores GraphQL", details=errors)
            return payload.get("data", {})

        raise ShopifyError(
            "Shopify no respondio correctamente despues de varios intentos",
            details=last_error,
        )

    def _backoff(self, attempt: int) -> float:
        exponential = self._settings.retry_base_delay * (2**attempt)
        return min(self._settings.retry_max_delay, exponential) + random.uniform(0, 0.25)

    def _http_retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(self._settings.retry_max_delay, max(0.0, float(retry_after)))
            except ValueError:
                pass
        return self._backoff(attempt)

    def _graphql_retry_delay(self, payload: dict[str, Any], attempt: int) -> float:
        cost = payload.get("extensions", {}).get("cost", {})
        throttle = cost.get("throttleStatus", {})
        requested = float(cost.get("requestedQueryCost") or 0)
        available = float(throttle.get("currentlyAvailable") or 0)
        restore_rate = float(throttle.get("restoreRate") or 0)
        if restore_rate > 0 and requested > available:
            calculated = (requested - available) / restore_rate
            return min(self._settings.retry_max_delay, max(calculated, self._backoff(attempt)))
        return self._backoff(attempt)

    @staticmethod
    def _response_details(response: httpx.Response) -> object:
        try:
            return response.json()
        except ValueError:
            return response.text[:500]

    async def request_client_credentials_token(
        self,
        shop: str,
        client_id: str,
        client_secret: str,
    ) -> dict[str, Any]:
        last_error: object = None
        payload: dict[str, Any] | None = None
        for attempt in range(self._settings.max_retries + 1):
            try:
                response = await self._http.post(
                    f"https://{shop}/admin/oauth/access_token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                    headers={"Accept": "application/json"},
                )
            except httpx.RequestError as exc:
                last_error = str(exc)
                if attempt >= self._settings.max_retries:
                    break
                await asyncio.sleep(self._backoff(attempt))
                continue

            if response.status_code in {429, 500, 502, 503, 504}:
                last_error = self._response_details(response)
                if attempt >= self._settings.max_retries:
                    break
                await asyncio.sleep(self._http_retry_delay(response, attempt))
                continue
            if response.is_error:
                raise ShopifyError(
                    "Shopify rechazo la generacion del access_token",
                    details={"status": response.status_code, "response": self._response_details(response)},
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise ShopifyError("Shopify devolvio una respuesta de token invalida") from exc
            break

        if payload is None:
            raise ShopifyError(
                "No fue posible generar el access_token despues de varios intentos",
                details=last_error,
            )

        if not payload.get("access_token") or not payload.get("expires_in"):
            raise ShopifyError("Respuesta de token incompleta recibida desde Shopify")
        return payload

    async def exchange_oauth_code(self, shop: str, code: str) -> dict[str, Any]:
        if not self._settings.shopify_api_key or not self._settings.shopify_api_secret:
            raise ShopifyError("Credenciales OAuth no configuradas", status_code=500)
        try:
            response = await self._http.post(
                f"https://{shop}/admin/oauth/access_token",
                json={"client_id": self._settings.shopify_api_key, "client_secret": self._settings.shopify_api_secret, "code": code},
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
            raise ShopifyError("No fue posible obtener el access_token de Shopify") from exc
        if not payload.get("access_token"):
            raise ShopifyError("Shopify no devolvio un access_token")
        return payload
