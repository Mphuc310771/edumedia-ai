import logging
import os
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from apps.api.auth import verify_api_key
from apps.api.auth_routes import router as auth_router
from apps.api.endpoints import generate_upload_url, process_agent_query, router as api_router
from apps.api.rate_limit import limiter
from apps.api.schemas import AgentQueryRequest, AgentQueryResponse, UploadUrlRequest, UploadUrlResponse
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
# Reload triggered for updated .env settings


@asynccontextmanager
async def lifespan(application: FastAPI):
    # startup
    from apps.aws.providers import get_runtime

    runtime = get_runtime()
    logger.info(
        "AgentSys started provider=aws env=%s ingest_mode=%s",
        settings.ENVIRONMENT,
        "event" if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else "sync",
    )
    if runtime.provider != "aws":
        raise RuntimeError("AgentSys only runs on AWS (S3, Rekognition, Transcribe, DynamoDB, Bedrock).")
    yield
    # shutdown (nothing to clean up)


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version=settings.APP_VERSION,
    description="Multi-modal media retrieval on Amazon S3, Rekognition, Transcribe, DynamoDB, and Bedrock.",
    docs_url="/docs",
    redoc_url=None,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add standard security headers for OWASP compliance and defense-in-depth."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(api_router, prefix="/api/v1/media", tags=["Media"])


@app.post("/api/upload-url", response_model=UploadUrlResponse, dependencies=[Depends(verify_api_key)], tags=["Media"], include_in_schema=False)
@app.post("/upload-url", response_model=UploadUrlResponse, dependencies=[Depends(verify_api_key)], tags=["Media"], include_in_schema=False)
def upload_url_alias(payload: UploadUrlRequest):
    return generate_upload_url(payload)


@app.post("/api/v1/agent/query", response_model=AgentQueryResponse, dependencies=[Depends(verify_api_key)], tags=["Search"], include_in_schema=False)
@app.post("/agent/query", response_model=AgentQueryResponse, dependencies=[Depends(verify_api_key)], tags=["Search"], include_in_schema=False)
@app.post("/api/search", response_model=AgentQueryResponse, dependencies=[Depends(verify_api_key)], tags=["Search"], include_in_schema=False)
@limiter.limit("20/minute")
def search_alias(request: Request, payload: AgentQueryRequest):
    return process_agent_query(request, payload)




@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = str(uuid.uuid4())
    logger.error(
        "unhandled request_id=%s %s %s",
        request_id,
        request.method,
        request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "Internal server error",
            "request_id": request_id,
        },
    )


@app.get("/health", tags=["Monitoring"])
def healthcheck():
    from apps.aws.providers import get_runtime

    runtime = get_runtime()
    in_lambda = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    body = {
        "status": "HEALTHY",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "provider": runtime.provider,
        "ingest_mode": "event" if in_lambda else "sync",
        "components": {
            "api": "ONLINE",
            "catalog": "ONLINE",
        },
    }
    from apps.aws.aws_services import ping_aws

    aws_ping = ping_aws(ttl_seconds=120)
    aws_status = aws_ping["status"]
    body["components"].update(aws_status)
    if aws_ping["errors"]:
        body["component_errors"] = aws_ping["errors"]
    if any(value == "OFFLINE" for value in aws_status.values()):
        body["status"] = "DEGRADED"
        if aws_status.get("transcribe") == "OFFLINE":
            body["message"] = (
                "Amazon Transcribe chưa bật trên account (SubscriptionRequired). "
                "Mở AWS Console → Amazon Transcribe một lần rồi restart backend. "
                "File audio sẽ fail cho đến khi service này ONLINE."
            )
    return body
