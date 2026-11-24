
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.services.auth_dependencies import get_current_user
from app.services.jwt_service import JWTService


TEST_SECRET = "test-jwt-secret-for-auth-dependency-tests"


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def test_user():
    return SimpleNamespace(
        id=uuid4(),
        username="alex.engineer",
        first_name="Alex",
        last_name="Morgan",
        company="MoveToAI",
        job_title="Software Engineer",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


def test_auth_me_returns_authenticated_user(test_user):
    app.dependency_overrides[get_current_user] = lambda: test_user

    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["username"] == "alex.engineer"
    assert response.json()["id"] == str(test_user.id)
    assert "password_hash" not in response.json()


def test_auth_me_requires_authentication():
    # The database dependency must not connect to real PostgreSQL
    # when authentication fails before user lookup.
    app.dependency_overrides[get_db] = lambda: object()

    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_invalid_token_returns_401():
    app.dependency_overrides[get_db] = lambda: object()

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": "Bearer invalid-token"
            },
        )

    assert response.status_code == 401
