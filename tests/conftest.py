import os

os.environ.setdefault("MEDIA_PROVIDER", "memory")
os.environ.setdefault("SEED_DEMO_ITEMS", "true")
os.environ.setdefault("ADMIN_API_KEY", "test-key")
os.environ.setdefault("ENVIRONMENT", "development")

import pytest
from fastapi.testclient import TestClient

from apps.aws.memory import reset_memory
from apps.aws.providers import reset_runtime
from apps.api.main import app
from config.settings import settings


@pytest.fixture(autouse=True)
def reset_state():
    settings.MEDIA_PROVIDER = "memory"
    settings.SEED_DEMO_ITEMS = True
    settings.ENVIRONMENT = "development"
    if not settings.ADMIN_API_KEY:
        settings.ADMIN_API_KEY = "test-key"
    reset_memory()
    reset_runtime()
    yield
    reset_memory()
    reset_runtime()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": settings.ADMIN_API_KEY or "test-key"}
