
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.main import app


@pytest.fixture
def mock_db():
    db = MagicMock()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    yield db

    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_db):
    return TestClient(app)


def test_health_endpoint(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_database_connection_success(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = (
        "0.8.7"
    )

    response = client.get("/api/v1/database/status")

    assert response.status_code == 200
    assert response.json() == {
        "status": "connected",
        "database": "PostgreSQL",
        "pgvector_version": "0.8.7",
    }

    mock_db.execute.assert_called_once()


def test_vector_extension_missing(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = (
        None
    )

    response = client.get("/api/v1/database/status")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "pgvector extension is not enabled"
    )


def test_database_unavailable(client, mock_db):
    mock_db.execute.side_effect = OperationalError(
        "SELECT 1",
        {},
        Exception("Connection refused"),
    )

    response = client.get("/api/v1/database/status")

    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"


def test_list_vectors(client, mock_db):
    rows = [
        {
            "id": 1,
            "content": "Payment transaction",
            "embedding": "[0.9,0.1,0.1]",
        }
    ]

    mock_db.execute.return_value.mappings.return_value.all.return_value = (
        rows
    )

    response = client.get("/api/v1/vectors")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["items"][0]["content"] == (
        "Payment transaction"
    )
