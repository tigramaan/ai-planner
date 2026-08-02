import base64
import os

os.environ.update(
    {
        "DATABASE_URL": "sqlite:///./test-planner.db",
        "OWNER_EMAIL": "tigramaan@gmail.com",
        "OWNER_INITIAL_PASSWORD": "correct-horse-battery-staple",
        "INITIAL_SETUP_TOKEN": "test-initial-setup-token-that-is-long-enough",
        "FAMILY_REGISTRATION_CODE": "family-registration-code-2026",
        "JWT_SECRET": "test-jwt-secret-that-is-at-least-thirty-two-bytes",
        "SECRET_MASTER_KEY": base64.urlsafe_b64encode(b"x" * 32).decode(),
        "COOKIE_SECURE": "false",
        "WORKER_SERVICE_TOKEN": "test-worker-service-token-that-is-long-enough",
        "VAPID_PUBLIC_KEY": "test-public-vapid-key",
    }
)

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    with TestClient(app) as value:
        yield value


@pytest.fixture
def logged_in(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "tigramaan@gmail.com", "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return client
