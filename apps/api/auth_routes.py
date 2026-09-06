from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from apps.api.auth import TOKEN_TTL_SECONDS, authenticate_password, issue_session_token

router = APIRouter()


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    expires_in: int
    username: str


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest):
    if not authenticate_password(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai tài khoản hoặc mật khẩu")
    username = payload.username.strip()
    return LoginResponse(
        token=issue_session_token(username),
        expires_in=TOKEN_TTL_SECONDS,
        username=username,
    )
