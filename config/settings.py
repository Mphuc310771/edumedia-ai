from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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

    # memory = local/CI contract; aws = real boto3 services
    MEDIA_PROVIDER: str = Field(default="memory")
    SEED_DEMO_ITEMS: bool = Field(default=False)

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

    # Optional S3-compatible endpoint for local experiments. Leave empty on AWS.
    S3_ENDPOINT_URL: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None

    TRANSCRIBE_POLL_SECONDS: int = 5
    TRANSCRIBE_MAX_WAIT_SECONDS: int = 120


settings = Settings()
