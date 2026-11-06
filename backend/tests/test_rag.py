# These are unit tests using fake database results. 
# In a future integration test, we'll insert real vectors and verify PostgreSQL's ranking directly.

from unittest.mock import MagicMock, patch
from uuid import uuid4
from app.rag_service import answer_document_question
from app.retrieval_service import RetrievedChunk


def test_rag_generates_grounded_answer():
    db = MagicMock()
    ai = MagicMock()

    ai.generate_embeddings.return_value = [
        [0.1] * 768
    ]

    ai.generate_grounded_answer.return_value = (
        "Refunds above $500 require approval. [1]"
    )

    chunks = [
        RetrievedChunk(
            content="Refunds above $500 require manager approval.",
            filename="policy.txt",
            page_number=2,
            chunk_index=3,
            distance=0.1,
        )
    ]

    with patch(
        "app.rag_service.search_chunks",
        return_value=chunks,
    ) as mock_search:

        result = answer_document_question(
            db=db,
            ai=ai,
            document_id=uuid4(),
            question="Which refunds need approval?",
        )

    assert result.context_found is True
    assert "above $500" in result.answer
    assert result.sources[0]["page_number"] == 2
    assert result.sources[0]["reference"] == 1

    mock_search.assert_called_once()

    ai.generate_grounded_answer.assert_called_once()

    context = (
        ai.generate_grounded_answer
        .call_args.kwargs["context"]
    )

    assert "[1]" in context
    assert "policy.txt" in context


def test_rag_handles_missing_context():
    db = MagicMock()
    ai = MagicMock()

    ai.generate_embeddings.return_value = [
        [0.1] * 768
    ]

    with patch(
        "app.rag_service.search_chunks",
        return_value=[],
    ):
        result = answer_document_question(
            db=db,
            ai=ai,
            document_id=uuid4(),
            question="What is the CEO's salary?",
        )

    assert result.context_found is False
    assert result.sources == []
    assert "could not find" in result.answer

    ai.generate_grounded_answer.assert_not_called()
