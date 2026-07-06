"""API key validation for internal service communication."""

from fastapi import Header, HTTPException, status

from app.core.config import settings


async def verify_api_key(
    x_ai_backend_api_key: str = Header(alias=settings.api_key_header, default=""),
) -> str:
    """Validate the internal API key from request headers."""
    if not x_ai_backend_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key header",
        )
    if x_ai_backend_api_key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return x_ai_backend_api_key
