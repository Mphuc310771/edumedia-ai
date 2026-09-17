from pathlib import Path
from typing import List, Optional

from pydantic import Field
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
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
        ]
    )

    AWS_REGION: str = Field(default="us-east-1")
    MEDIA_BUCKET: str = Field(default="agentsys-media-bucket")
    METADATA_TABLE: str = Field(default="AgentSysMediaMetadata")
    TRANSCRIBE_OUTPUT_PREFIX: str = "transcripts/"
    BEDROCK_MODEL_ID: str = Field(
        default="amazon.nova-lite-v1:0"
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


settings = Settings()
# Reload settings
