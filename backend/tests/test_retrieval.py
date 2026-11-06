# testing retrieval and generation independently.
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import pytest

from app.retrieval_service import search_chunks


def test_search_returns_ranked_chunks():
    db = MagicMock()

    db.execute.return_value.all.return_value = [
        (
            SimpleNamespace(
                content="Refunds above $500 need approval",
                page_number=1,
                chunk_index=0,
            ),
            "policy.txt",
            0.1,
        ),
        (
            SimpleNamespace(
                content="Refunds take five days",
                page_number=2,
                chunk_index=1,
            ),
            "policy.txt",
            0.3,
        ),
    ]

    results = search_chunks(
        db=db,
        query_vector=[0.1] * 768,
        document_id=uuid4(),
        limit=2,
    )

    assert len(results) == 2
    assert results[0].content.startswith("Refunds above")
    assert results[0].similarity == pytest.approx(0.9)
    assert results[1].similarity == pytest.approx(0.7)

    db.execute.assert_called_once()


def test_reject_invalid_vector_dimensions():
    db = MagicMock()

    with pytest.raises(
        ValueError,
        match="768-dimensional",
    ):
        search_chunks(
            db=db,
            query_vector=[0.1, 0.2, 0.3],
            document_id=uuid4(),
        )

    db.execute.assert_not_called()
