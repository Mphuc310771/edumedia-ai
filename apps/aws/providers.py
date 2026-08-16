from __future__ import annotations

from dataclasses import dataclass

from apps.aws.local_gpu import LocalGPUVision
from apps.aws.memory import (
    MemoryCatalog,
    MemoryMetrics,
    MemoryObjectStore,
    MemoryPlanner,
    MemorySpeech,
    MemoryVision,
)
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
    provider: str


_RUNTIME: Runtime | None = None


def get_runtime() -> Runtime:
    global _RUNTIME
    if _RUNTIME is None:
        _RUNTIME = build_runtime(settings.MEDIA_PROVIDER)
    return _RUNTIME


def build_runtime(provider: str) -> Runtime:
    if provider == "aws":
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
    return Runtime(
        catalog=MemoryCatalog(seed=settings.SEED_DEMO_ITEMS),
        store=MemoryObjectStore(),
        vision=LocalGPUVision(fallback_vision=MemoryVision()),
        speech=MemorySpeech(),
        planner=MemoryPlanner(),
        metrics=MemoryMetrics(),
        provider="memory",
    )


def reset_runtime() -> None:
    global _RUNTIME
    _RUNTIME = None
