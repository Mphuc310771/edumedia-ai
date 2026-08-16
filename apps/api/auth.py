import logging

from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from config.settings import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    expected = settings.ADMIN_API_KEY
    if settings.ENVIRONMENT == "development" and not expected:
        return "dev-no-auth"

    incoming = api_key or ""
    if settings.ENVIRONMENT == "development" and not incoming:
        return expected or "dev-no-auth"

    if not expected or incoming != expected:
        logger.warning("Rejected API request with missing or invalid X-API-Key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key in request header X-API-Key",
        )
    return incoming
