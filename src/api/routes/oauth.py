from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.api.dependencies import get_oauth_service
from src.application.oauth_service import OAuthService


router = APIRouter(tags=["oauth"])


@router.get("/app-shopify")
async def shopify_callback(
    request: Request,
    service: Annotated[OAuthService, Depends(get_oauth_service)],
) -> dict:
    return await service.complete_installation(dict(request.query_params))
