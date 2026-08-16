import logging
import uuid

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from apps.api.endpoints import router as api_router
from apps.api.rate_limit import limiter
from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    version=settings.APP_VERSION,
    description="Multi-modal media retrieval on Amazon S3, Rekognition, Transcribe, DynamoDB, and Bedrock.",
    docs_url="/docs",
    redoc_url=None,
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
app.include_router(api_router, prefix="/api/v1/media", tags=["Media"])


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
    body = {
        "status": "HEALTHY",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "provider": runtime.provider,
        "components": {
            "api": "ONLINE",
            "catalog": "ONLINE",
        },
    }
    if runtime.provider == "aws":
        from apps.aws.aws_services import ping_aws

        aws_status = ping_aws()
        body["components"].update(aws_status)
        if any(value == "OFFLINE" for value in aws_status.values()):
            body["status"] = "DEGRADED"
            return JSONResponse(status_code=503, content=body)
    return body
