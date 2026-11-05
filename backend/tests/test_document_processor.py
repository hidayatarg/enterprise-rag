import pytest

from app.document_processor import (
    process_document,
    split_text,
)


def test_short_text_creates_one_chunk():
    chunks = split_text("Hello RAG")

    assert len(chunks) == 1
    assert chunks[0] == "Hello RAG"


def test_long_text_creates_overlapping_chunks():
    text = "A" * 1200

    chunks = split_text(
        text,
        chunk_size=500,
        overlap=100,
    )

    assert len(chunks) == 3
    assert len(chunks[0]) == 500
    assert chunks[0][-100:] == chunks[1][:100]


def test_empty_document_creates_no_chunks():
    assert split_text("   ") == []


def test_invalid_chunk_configuration():
    with pytest.raises(ValueError):
        split_text(
            "Hello",
            chunk_size=100,
            overlap=100,
        )


def test_txt_document_processing():
    data = b"Refunds require transaction IDs."

    chunks = process_document(
        data,
        "policy.txt",
    )

    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_index == 0
    assert "Refunds" in chunks[0].content


def test_unsupported_document():
    with pytest.raises(ValueError):
        process_document(
            b"test",
            "document.csv",
        )
