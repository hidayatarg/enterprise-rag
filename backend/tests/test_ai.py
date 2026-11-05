
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from ollama import ResponseError

from app.ai_service import get_ai_service
from app.main import app


@pytest.fixture
def fake_ai():
    service = MagicMock()

    service.chat_model = "llama3.2"
    service.embedding_model = "embeddinggemma"

    app.dependency_overrides[get_ai_service] = (
        lambda: service
    )

    yield service

    app.dependency_overrides.pop(get_ai_service, None)


@pytest.fixture
def client(fake_ai):
    with TestClient(app) as test_client:
        yield test_client


def test_generate_answer(client, fake_ai):
    fake_ai.generate_answer.return_value = (
        "RAG combines retrieval with generation."
    )

    response = client.post(
        "/api/v1/ai/chat",
        json={
            "question": "What is RAG?",
        },
    )

    assert response.status_code == 200
    assert response.json()["model"] == "llama3.2"
    assert "retrieval" in response.json()["answer"]

    fake_ai.generate_answer.assert_called_once_with(
        "What is RAG?"
    )


def test_generate_embedding(client, fake_ai):
    fake_ai.generate_embeddings.return_value = [
        [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
    ]

    response = client.post(
        "/api/v1/ai/embed",
        json={
            "text": "Refund request",
        },
    )

    assert response.status_code == 200
    assert response.json()["dimensions"] == 6
    assert response.json()["preview"] == [
        0.1, 0.2, 0.3, 0.4, 0.5
    ]


def test_empty_question_validation(client):
    response = client.post(
        "/api/v1/ai/chat",
        json={"question": ""},
    )

    assert response.status_code == 422


def test_ollama_failure(client, fake_ai):
    fake_ai.generate_answer.side_effect = ResponseError(
        "Model not found",
        status_code=404,
    )

    response = client.post(
        "/api/v1/ai/chat",
        json={"question": "Hello"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "AI service unavailable"
    )
