import base64
import hashlib
import hmac
import json
import logging
import time
from typing import Optional

from fastapi import HTTPException, Request, Security, status
from fastapi.security.api_key import APIKeyHeader
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer

from config.settings import settings

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER_NAME, auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

TOKEN_TTL_SECONDS = 12 * 3600


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _get_live_credentials() -> tuple[str, str]:
    expected_user = (settings.ADMIN_USERNAME or "admin").strip()
    expected_pass = (settings.ADMIN_PASSWORD or settings.ADMIN_API_KEY or "").strip()
    try:
        from config.settings import _ENV_FILE

        if _ENV_FILE.exists():
            for line in _ENV_FILE.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("ADMIN_PASSWORD="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        expected_pass = val
                elif line.startswith("ADMIN_API_KEY=") and not expected_pass:
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        expected_pass = val
                elif line.startswith("ADMIN_USERNAME="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        expected_user = val
    except Exception:
        pass
    return expected_user, expected_pass


def _secret() -> bytes:
    """Derive the HMAC signing secret from configured credentials."""
    _, key = _get_live_credentials()
    secret = key or settings.ADMIN_API_KEY or "agentsys-dev-only"
    if secret == "agentsys-dev-only":
        logger.warning(
            "auth_secret_fallback: Using default secret. "
            "Set ADMIN_API_KEY or ADMIN_PASSWORD in .env for production.",
        )
    return secret.encode("utf-8")


def issue_session_token(username: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    now = int(time.time())
    payload = _b64url(
        json.dumps(
            {"sub": username, "iat": now, "exp": now + TOKEN_TTL_SECONDS},
            separators=(",", ":"),
        ).encode()
    )
    signing = f"{header}.{payload}".encode()
    sig = _b64url(hmac.new(_secret(), signing, hashlib.sha256).digest())
    return f"{header}.{payload}.{sig}"


def verify_session_token(token: str) -> Optional[str]:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing = f"{header_b64}.{payload_b64}".encode()
        expected = hmac.new(_secret(), signing, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
            return None
        claims = json.loads(_b64url_decode(payload_b64))
        if int(claims.get("exp", 0)) < int(time.time()):
            return None
        return str(claims.get("sub") or "")
    except Exception:
        return None


def _eq(left: str, right: str) -> bool:
    left_b = left.encode("utf-8")
    right_b = right.encode("utf-8")
    if len(left_b) != len(right_b):
        hmac.compare_digest(left_b, left_b)
        return False
    return hmac.compare_digest(left_b, right_b)


def authenticate_password(username: str, password: str) -> bool:
    expected_user, expected_pass = _get_live_credentials()
    if not expected_pass:
        return False
    return _eq(username.strip(), expected_user) and _eq(password, expected_pass)


def verify_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
) -> str:
    expected = settings.ADMIN_API_KEY

    if bearer_auth and bearer_auth.credentials:
        user = verify_session_token(bearer_auth.credentials)
        if user:
            return f"user:{user}"

    incoming = api_key or ""
    if expected and hmac.compare_digest(incoming, expected):
        return incoming

    logger.warning("Rejected API request path=%s", request.url.path)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Cần đăng nhập hoặc X-API-Key hợp lệ",
    )
