from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ShopifyError(Exception):
    def __init__(self, message: str, status_code: int = 502, details: object = None):
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ShopifyError)
    async def handle_shopify_error(_: Request, exc: ShopifyError) -> JSONResponse:
        content = {"detail": exc.message}
        if exc.details is not None:
            content["shopify_error"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=content)
