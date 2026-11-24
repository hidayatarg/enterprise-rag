
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.database import get_db
from app.services.user_service import (
    UserService,
    UsernameAlreadyExistsError,
)


REGISTER_PAYLOAD = {
    "username": "alex.engineer",
    "first_name": "Alex",
    "last_name": "Morgan",
    "company": "MoveToAI",
    "job_title": "Software Engineer",
    "password": "ExampleRegistrationPassword2026!",
}


def fake_db():
    yield object()


def setup_function():
    app.dependency_overrides[get_db] = fake_db


def teardown_function():
    app.dependency_overrides.clear()


def test_register_user_returns_201(monkeypatch):
    user_id = uuid4()

    def fake_register_user(self, request):
        return SimpleNamespace(
            id=user_id,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name,
            company=request.company,
            job_title=request.job_title,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        UserService,
        "register_user",
        fake_register_user,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json=REGISTER_PAYLOAD,
        )

    assert response.status_code == 201

    data = response.json()

    assert data["username"] == "alex.engineer"
    assert data["first_name"] == "Alex"
    assert data["company"] == "MoveToAI"
    assert data["id"] == str(user_id)
    assert "password" not in data
    assert "password_hash" not in data


def test_duplicate_username_returns_409(monkeypatch):
    def fake_register_user(self, request):
        raise UsernameAlreadyExistsError()

    monkeypatch.setattr(
        UserService,
        "register_user",
        fake_register_user,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json=REGISTER_PAYLOAD,
        )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Username is already registered."
    )


def test_registration_rejects_short_password():
    payload = {
        **REGISTER_PAYLOAD,
        "password": "short",
    }

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json=payload,
        )

    assert response.status_code == 422


def test_registration_normalizes_username(monkeypatch):
    captured = {}

    def fake_register_user(self, request):
        captured["username"] = request.username

        return SimpleNamespace(
            id=uuid4(),
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name,
            company=request.company,
            job_title=request.job_title,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        UserService,
        "register_user",
        fake_register_user,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                **REGISTER_PAYLOAD,
                "username": "Alex.Engineer",
            },
        )

    assert response.status_code == 201
    assert captured["username"] == "alex.engineer"
