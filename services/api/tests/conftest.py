import base64
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

os.environ.update(
    {
        "DATABASE_URL": "sqlite://",
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
from sqlalchemy import create_engine
from sqlalchemy.orm import close_all_sessions
from sqlalchemy.pool import StaticPool

from app import database as test_database

# One shared connection keeps the in-memory database accessible to TestClient threads.
# Rebind the existing session factory before importing application routers.
test_database.engine.dispose()
engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
)
engine.update_execution_options(
    qa_resource={
        "owner": "aiplanner",
        "project": "aiplanner",
        "run": os.environ.get("QA_RESOURCE_RUN", uuid4().hex),
        "purpose": "api-tests",
        "expiry": os.environ.get(
            "QA_RESOURCE_EXPIRY", (datetime.now(UTC) + timedelta(minutes=15)).isoformat()
        ),
    }
)
test_database.engine = engine
test_database.SessionLocal.configure(bind=engine)
Base = test_database.Base

from app.main import app


@pytest.fixture(autouse=True)
def database():
    Base.metadata.drop_all(engine)
    try:
        Base.metadata.create_all(engine)
        yield
    finally:
        close_all_sessions()
        Base.metadata.drop_all(engine)


def pytest_sessionfinish(session, exitstatus):
    close_all_sessions()
    engine.dispose()


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
