from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.ai_service import get_ai_service
from app.database import get_db
from app.main import app


@pytest.fixture
def client():
    fake_db = MagicMock()
    fake_ai = MagicMock()

    app.dependency_overrides[get_db] = (
        lambda: fake_db
    )

    app.dependency_overrides[get_ai_service] = (
        lambda: fake_ai
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_upload_txt_success(client):
    document_id = uuid4()

    with patch(
        "app.main.ingest_document",
        return_value=(document_id, 1),
    ) as mock_ingest:
        response = client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "policy.txt",
                    b"Customers may request refunds.",
                    "text/plain",
                ),
            },
        )

    assert response.status_code == 201
    assert response.json()["status"] == "indexed"
    assert response.json()["document_id"] == str(
        document_id
    )
    assert response.json()["chunks_created"] == 1

    mock_ingest.assert_called_once()


def test_reject_unsupported_file(client):
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "data.csv",
                b"example,data",
                "text/csv",
            ),
        },
    )

    assert response.status_code == 400


def test_reject_empty_file(client):
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "empty.txt",
                b"",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400


def test_reject_file_over_size_limit(client):
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "large.txt",
                b"A" * (5 * 1024 * 1024 + 1),
                "text/plain",
            ),
        },
    )

    assert response.status_code == 413


def test_reject_txt_without_extractable_text(client):
    response = client.post(
        "/api/v1/documents/upload",
        files={
            "file": (
                "blank.txt",
                b"   ",
                "text/plain",
            ),
        },
    )

    assert response.status_code == 400
