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

    logger = logging.getLogger(__name__)
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
