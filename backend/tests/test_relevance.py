
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.retrieval_service import search_chunks


def test_query_contains_relevance_filter():
    db = MagicMock()
    db.execute.return_value.all.return_value = []

    search_chunks(
        db=db,
        query_vector=[0.1] * 768,
        document_id=uuid4(),
        min_similarity=0.45,
    )

    statement = db.execute.call_args.args[0]

    compiled = statement.compile(
        dialect=postgresql.dialect()
    )

    sql = str(compiled)

    # Verify SQL contains cosine distance and filtering.
    assert "<=>" in sql
    assert "document_id" in sql
    assert "<=" in sql


def test_retrieved_chunk_similarity():
    db = MagicMock()

    db.execute.return_value.all.return_value = [
        (
            SimpleNamespace(
                content="Refund approval required",
                page_number=1,
                chunk_index=0,
            ),
            "policy.txt",
            0.35,
        )
    ]

    results = search_chunks(
        db=db,
        query_vector=[0.1] * 768,
        document_id=uuid4(),
    )

    assert len(results) == 1
    assert abs(results[0].similarity - 0.65) < 0.00001
