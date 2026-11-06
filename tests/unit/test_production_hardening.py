"""Integration tests for production security hardening."""

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def prod_client():
    """A client whose app believes it is in production."""
    from agent.src.settings import settings

    with (
        patch.object(type(settings), "is_production", property(lambda _self: True)),
        patch.dict("os.environ", {"ENVIRONMENT": "production", "ENABLE_AUTH": "true"}),
    ):
        from agent.aegra.http_app import app

        yield TestClient(app)


def test_all_security_headers_present_in_production(prod_client):
    """Test that all security headers are present in production responses."""
    response = prod_client.get("/")

    required_headers = [
        "X-Content-Type-Options",
        "X-Frame-Options",
        "X-XSS-Protection",
        "Strict-Transport-Security",
        "Content-Security-Policy",
        "Referrer-Policy",
        "Permissions-Policy",
    ]

    for header in required_headers:
        assert header in response.headers, f"Missing security header: {header}"


def test_production_mode_config_validation():
    """Test that production mode validates configuration at startup."""
    from agent.src.settings import Settings, validate_config

    prod_settings = Settings(ENVIRONMENT="production", ENABLE_AUTH=False)

    with pytest.raises(Exception, match="ENABLE_AUTH must be true"):
        validate_config(prod_settings)

    prod_settings_valid = Settings(ENVIRONMENT="production", ENABLE_AUTH=True)
    validate_config(prod_settings_valid)
