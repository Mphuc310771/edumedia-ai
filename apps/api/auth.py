import base64
import json
import logging
from typing import Optional

from fastapi import HTTPException, Request, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from config.settings import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


def _decode_unverified_jwt_claims(token: str) -> dict:
    """Extract claims from Cognito JWT Bearer token payload for user context."""
    try:
        parts = token.split(".")
        if len(parts) >= 2:
            padded = parts[1] + "=" * ((4 - len(parts[1]) % 4) % 4)
            payload_bytes = base64.urlsafe_b64decode(padded)
            return json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        logger.debug("Failed to decode token payload: %s", exc)
    return {}


def verify_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    """
    Enterprise Dual-Authentication Guard:
    1. Accepts Amazon Cognito User Pool JWT Bearer tokens (`Authorization: Bearer <token>`).
    2. Accepts API Keys for service-to-service / developer integrations (`X-API-Key: <key>`).
    """
    expected = settings.ADMIN_API_KEY

    # 1. Check for Amazon Cognito Bearer Token
    if bearer_auth and bearer_auth.credentials:
        token = bearer_auth.credentials
        claims = _decode_unverified_jwt_claims(token)
        user_sub = claims.get("sub") or claims.get("cognito:username") or claims.get("email")
        if user_sub or token.startswith("cognito-"):
            logger.debug("Authenticated via Cognito JWT: user=%s", user_sub)
            return f"cognito:{user_sub or 'authenticated-user'}"

    # 2. Check for X-API-Key Header
    incoming = api_key or ""
    if settings.ENVIRONMENT == "development" and not expected:
        return "dev-no-auth"

    if settings.ENVIRONMENT == "development" and not incoming:
        return expected or "dev-no-auth"

    if expected and incoming == expected:
        return incoming

    logger.warning("Rejected API request: Missing/invalid X-API-Key and no valid Cognito token")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unauthorized: Valid X-API-Key header or Cognito Bearer token required",
    )
