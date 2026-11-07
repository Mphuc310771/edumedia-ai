from __future__ import annotations

from dataclasses import dataclass

from apps.aws.protocols import (
    Catalog,
    Metrics,
    ObjectStore,
    QueryPlanner,
    SpeechAnalyzer,
    VisionAnalyzer,
)
from config.settings import settings


@dataclass
class Runtime:
    catalog: Catalog
    store: ObjectStore
    vision: VisionAnalyzer
    speech: SpeechAnalyzer
    planner: QueryPlanner
    metrics: Metrics
    provider: str = "aws"


_RUNTIME: Runtime | None = None


def get_runtime() -> Runtime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = build_runtime()
    return _RUNTIME


def build_runtime() -> Runtime:
    import logging
    import os
    import boto3

    logger = logging.getLogger(__name__)

    # In local development without AWS credentials, gracefully fallback to in-memory Moto
    is_lambda = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
    has_creds = False
    if not is_lambda:
        try:
            session = boto3.Session(region_name=settings.AWS_REGION)
            has_creds = session.get_credentials() is not None
        except Exception:
            has_creds = False

    if not is_lambda and not has_creds and settings.ENVIRONMENT == "development":
        logger.warning(
            "No AWS credentials found in local environment. "
            "Activating Mock AWS Runtime with seed records for offline UI testing."
        )
        try:
            from moto import mock_aws
            from tests.fakes import build_test_runtime, seed_moto_catalog, setup_moto_infra

            mock = mock_aws()
            mock.start()
            setup_moto_infra()
            seed_moto_catalog()
            return build_test_runtime()
        except Exception as err:
            logger.error("Failed to initialize mock AWS runtime: %s", err)

    logger.info(
        "runtime_provider=aws bucket=%s table=%s region=%s",
        settings.MEDIA_BUCKET,
        settings.METADATA_TABLE,
        settings.AWS_REGION,
    )
    from apps.aws.aws_services import (
        BedrockPlanner,
        CloudWatchMetrics,
        DynamoCatalog,
        RekognitionVision,
        S3ObjectStore,
        TranscribeSpeech,
    )

    return Runtime(
        catalog=DynamoCatalog(),
        store=S3ObjectStore(),
        vision=RekognitionVision(),
        speech=TranscribeSpeech(),
        planner=BedrockPlanner(),
        metrics=CloudWatchMetrics(),
        provider="aws",
    )


def reset_runtime() -> None:
    global _RUNTIME
    _RUNTIME = None
