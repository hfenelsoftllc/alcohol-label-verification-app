"""Shared test fixtures."""

import base64

import pytest
from fastapi.testclient import TestClient

from app import session
from app.main import app
from batch import store

# A real (tiny) 1x1 PNG — passes the magic-byte image check.
PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
PNG_1X1_B64 = base64.b64encode(PNG_1X1).decode()


@pytest.fixture
def client() -> TestClient:
    store.clear()
    session.clear()
    # https://testserver (not the default http://) so the Secure session
    # cookie set on the first request (ISSUE 3.7) round-trips on later ones.
    test_client = TestClient(app, base_url="https://testserver")
    test_client.get("/health")
    return test_client


@pytest.fixture
def session_id(client: TestClient) -> str:
    """The auth session id (ISSUE 3.7) the `client` fixture has a cookie for."""
    return session.validate_cookie(client.cookies[session.COOKIE_NAME])


@pytest.fixture
def application_data() -> dict:
    return {
        "brand": "Stone's Throw",
        "class_type": "Vodka",
        "abv": "40% Alc. by Vol.",
        "net_contents": "750 mL",
        "name_address": "Stone's Throw Distillery, Louisville, KY",
        "country_of_origin": "United States",
        "government_warning": (
            "GOVERNMENT WARNING: (1) According to the Surgeon General, women "
            "should not drink alcoholic beverages during pregnancy because of "
            "the risk of birth defects. (2) Consumption of alcoholic beverages "
            "impairs your ability to drive a car or operate machinery, and may "
            "cause health problems."
        ),
    }
