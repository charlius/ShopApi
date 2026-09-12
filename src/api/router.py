from fastapi import APIRouter

from src.api.routes import inventory, oauth, products


api_router = APIRouter()
api_router.include_router(oauth.router)
api_router.include_router(products.router, prefix="/api/v1")
api_router.include_router(inventory.router, prefix="/api/v1")


@api_router.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
