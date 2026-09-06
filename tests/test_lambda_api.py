"""Tests for apps.lambda_handlers.api (Mangum handler wrapper)."""


def test_lambda_api_handler_is_callable():
    """Verify the Mangum handler is importable and callable."""
    from apps.lambda_handlers.api import handler

    assert callable(handler)


def test_lambda_api_handler_wraps_fastapi_app():
    """The handler must wrap the same FastAPI app used elsewhere."""
    from apps.api.main import app
    from apps.lambda_handlers.api import handler

    assert handler.app is app
