import os

os.environ.setdefault("ADMIN_API_KEY", "test-key")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")

import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

import apps.aws.providers as providers
from apps.aws.providers import reset_runtime
from apps.api.main import app
from config.settings import settings
from tests.fakes import build_test_runtime, seed_moto_catalog, setup_moto_infra

ONLINE = {name: "ONLINE" for name in ("sts", "s3", "dynamodb", "rekognition", "transcribe", "bedrock")}


@pytest.fixture(autouse=True)
def moto_aws_runtime(monkeypatch):
    settings.ENVIRONMENT = "development"
    if not settings.ADMIN_API_KEY:
        settings.ADMIN_API_KEY = "test-key"

    with mock_aws():
        setup_moto_infra()
        seed_moto_catalog()
        monkeypatch.setattr(providers, "build_runtime", build_test_runtime)
        monkeypatch.setattr(
            "apps.aws.aws_services.ping_aws",
            lambda ttl_seconds=0: {"status": dict(ONLINE), "errors": {}},
        )
        reset_runtime()
        yield
        reset_runtime()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": settings.ADMIN_API_KEY or "test-key"}
