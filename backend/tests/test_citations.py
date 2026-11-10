
"""
Tests for RAG citation validation.

Validates:
1. Correct citations.
2. Nonexistent source references.
3. Fabricated quotations.
4. Missing citations.
5. Empty quotations.
6. Whitespace normalization.
7. Citations referencing the wrong source.
8. Model abstention.

Run:
    uv run pytest tests/test_citations.py -v
"""

import pytest
from pydantic import ValidationError

from app.citation_validator import validate_citations
from app.rag_schemas import (
    EvidenceCitation,
    GroundedAnswer,
)
from app.retrieval_service import RetrievedChunk


POLICY = "Refunds above $500 require manager approval."


def make_chunks() -> list[RetrievedChunk]:
    """Create sample retrieved document chunks."""
    return [
        RetrievedChunk(
            content=POLICY,
            filename="policy.txt",
            page_number=1,
            chunk_index=0,
            distance=0.2,
        )
    ]


def make_grounded_answer(
    answer: str,
    quote: str,
    reference: int = 1,
) -> GroundedAnswer:
    """Create a supported answer with one citation."""
    return GroundedAnswer(
        answer=answer,
        sufficient_evidence=True,
        citations=[
            EvidenceCitation(
                reference=reference,
                quote=quote,
            )
        ],
    )


# --------------------------------------------------
# TEST 1: Valid citation
# --------------------------------------------------

def test_valid_citation():
    result = make_grounded_answer(
        answer="Manager approval is required above $500.",
        quote=POLICY,
    )

    assert validate_citations(result, make_chunks()) is True


# --------------------------------------------------
# TEST 2: Nonexistent reference
# --------------------------------------------------

def test_reject_nonexistent_source():
    result = make_grounded_answer(
        answer="Approval is required.",
        quote=POLICY,
        reference=9,
    )

    assert validate_citations(result, make_chunks()) is False


# --------------------------------------------------
# TEST 3: Fabricated quotation
# --------------------------------------------------

def test_reject_fabricated_quote():
    result = make_grounded_answer(
        answer="All refunds require approval.",
        quote="All refunds require approval.",
    )

    assert validate_citations(result, make_chunks()) is False


# --------------------------------------------------
# TEST 4: Missing citations
# --------------------------------------------------

def test_reject_missing_citations():
    """
    GroundedAnswer must reject supported answers without
    citations before validate_citations() is called.
    """
    with pytest.raises(
        ValidationError,
        match="Sufficient evidence requires",
    ):
        GroundedAnswer(
            answer="Refunds require approval.",
            sufficient_evidence=True,
            citations=[],
        )


# --------------------------------------------------
# TEST 5: Empty quotation
# --------------------------------------------------

def test_reject_empty_quote():
    """
    EvidenceCitation requires at least one character
    in the supporting quote.
    """
    with pytest.raises(ValidationError):
        EvidenceCitation(
            reference=1,
            quote="",
        )


# --------------------------------------------------
# TEST 6: Whitespace normalization
# --------------------------------------------------

def test_valid_citation_with_extra_whitespace():
    """
    Citation validator normalizes whitespace before
    checking whether a quotation exists in the source.
    """
    result = make_grounded_answer(
        answer="Manager approval is required above $500.",
        quote=(
            "Refunds above $500   require\n"
            "manager approval."
        ),
    )

    assert validate_citations(result, make_chunks()) is True


# --------------------------------------------------
# TEST 7: Citation points to wrong source
# --------------------------------------------------

def test_reject_quote_from_different_source():
    chunks = [
        RetrievedChunk(
            content=POLICY,
            filename="refund-policy.txt",
            page_number=1,
            chunk_index=0,
            distance=0.1,
        ),
        RetrievedChunk(
            content="Employees receive 20 vacation days.",
            filename="hr-policy.txt",
            page_number=1,
            chunk_index=0,
            distance=0.3,
        ),
    ]

    result = make_grounded_answer(
        answer="Refunds above $500 require approval.",
        quote=POLICY,
        reference=2,
    )

    # The quotation exists in source 1, not source 2.
    assert validate_citations(result, chunks) is False


# --------------------------------------------------
# TEST 8: Model abstention
# --------------------------------------------------

def test_reject_insufficient_evidence():
    """
    An unsupported answer must not pass citation
    validation, even when its structure is valid.
    """
    result = GroundedAnswer(
        answer="I could not find this information.",
        sufficient_evidence=False,
        citations=[],
    )

    assert validate_citations(result, make_chunks()) is False
