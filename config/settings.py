import json
from pathlib import Path
from typing import List, Optional, Union

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always load agent_sys/.env, even if uvicorn is started from another folder.
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Centralised application settings loaded from environment variables and .env file.

    All AWS credentials are optional — boto3 resolves them automatically via
    its standard credential chain (env → ~/.aws → instance profile).
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "AgentSys"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = Field(
        default="development",
        description="development | production",
    )

    API_KEY_HEADER_NAME: str = "X-API-Key"
    ADMIN_API_KEY: str = Field(default="", description="Required in production")
    ADMIN_USERNAME: str = Field(default="admin")
    ADMIN_PASSWORD: str = Field(
        default="",
        description="Login password. Empty = use ADMIN_API_KEY",
    )
    FRONTEND_ORIGIN_URL: Optional[str] = Field(
        default=None,
        description="Production frontend URL or * (overrides/augments ALLOWED_ORIGINS)",
    )
    ALLOWED_ORIGINS: Union[List[str], str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Union[str, List[str], None]) -> List[str]:
        default_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
        if value is None:
            return default_origins
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return default_origins
            if value.startswith("[") and value.endswith("]"):
                try:
                    parsed = json.loads(value)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            parts = [part.strip() for part in value.split(",") if part.strip()]
            if "*" in parts:
                return ["*"]
            # Merge with default local origins
            combined = list(dict.fromkeys(default_origins + parts))
            return combined
        if isinstance(value, list):
            items = [str(x).strip() for x in value if str(x).strip()]
            if "*" in items:
                return ["*"]
            return list(dict.fromkeys(default_origins + items))
        return default_origins

    AWS_REGION: str = Field(default="us-east-1")
    MEDIA_BUCKET: str = Field(default="agentsys-media-bucket")
    METADATA_TABLE: str = Field(default="AgentSysMediaMetadata")
    TRANSCRIBE_OUTPUT_PREFIX: str = "transcripts/"
    BEDROCK_MODEL_ID: str = Field(
        default="us.amazon.nova-pro-v1:0"
    )
    BEDROCK_REGION: Optional[str] = Field(
        default=None,
        description="Override region for Bedrock if the stack region has no model access",
    )
    CLOUDWATCH_NAMESPACE: str = "AgentSys"
    INGEST_QUEUE_URL: Optional[str] = Field(
        default=None,
        description="SQS queue URL for agentsys-ingest-queue",
    )

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_SESSION_TOKEN: Optional[str] = None

    TRANSCRIBE_POLL_SECONDS: int = 5
    TRANSCRIBE_MAX_WAIT_SECONDS: int = 180

    def model_post_init(self, __context: object) -> None:
        if self.FRONTEND_ORIGIN_URL:
            extra = [x.strip() for x in self.FRONTEND_ORIGIN_URL.split(",") if x.strip()]
            if "*" in extra:
                self.ALLOWED_ORIGINS = ["*"]
            elif self.ALLOWED_ORIGINS != ["*"]:
                self.ALLOWED_ORIGINS = list(dict.fromkeys(list(self.ALLOWED_ORIGINS) + extra))


settings = Settings()
# Reload settings
