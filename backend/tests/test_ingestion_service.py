from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.document_processor import TextChunk
from app.ingestion_service import ingest_document
from app.models import Document, DocumentChunk


def test_ingestion_saves_document_and_vector():
    db = MagicMock()
    ai = MagicMock()

    ai.generate_embeddings.return_value = [
        [0.1] * 768
    ]

    def assign_document_id():
        document = db.add.call_args_list[0].args[0]
        document.id = uuid4()

    db.flush.side_effect = assign_document_id

    chunks = [
        TextChunk(
            content="Refunds require approval.",
            page_number=1,
            chunk_index=0,
        )
    ]

    document_id, count = ingest_document(
        db=db,
        ai=ai,
        filename="policy.txt",
        content_type="text/plain",
        chunks=chunks,
    )

    assert count == 1
    assert document_id is not None

    added_objects = [
        call.args[0]
        for call in db.add.call_args_list
    ]

    assert any(
        isinstance(obj, Document)
        for obj in added_objects
    )

    saved_chunks = [
        obj
        for obj in added_objects
        if isinstance(obj, DocumentChunk)
    ]

    assert len(saved_chunks) == 1
    assert len(saved_chunks[0].embedding) == 768

    db.commit.assert_called_once()


def test_invalid_embedding_rolls_back():
    db = MagicMock()
    ai = MagicMock()

    ai.generate_embeddings.return_value = [
        [0.1, 0.2, 0.3]
    ]

    chunks = [
        TextChunk(
            content="Payment refund policy",
            page_number=1,
            chunk_index=0,
        )
    ]

    with pytest.raises(
        ValueError,
        match="Expected 768 dimensions",
    ):
        ingest_document(
            db=db,
            ai=ai,
            filename="policy.txt",
            content_type="text/plain",
            chunks=chunks,
        )

    db.rollback.assert_called_once()
    db.commit.assert_not_called()
