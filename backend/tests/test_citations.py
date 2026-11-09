
from app.citation_validator import validate_citations
from app.rag_schemas import (
    EvidenceCitation,
    GroundedAnswer,
)
from app.retrieval_service import RetrievedChunk


def make_chunks():
    return [
        RetrievedChunk(
            content=(
                "Refunds above $500 require "
                "manager approval."
            ),
            filename="policy.txt",
            page_number=1,
            chunk_index=0,
            distance=0.2,
        )
    ]


def test_valid_citation():
    result = GroundedAnswer(
        answer="Manager approval is required above $500.",
        sufficient_evidence=True,
        citations=[
            EvidenceCitation(
                reference=1,
                quote=(
                    "Refunds above $500 require "
                    "manager approval."
                ),
            )
        ],
    )

    assert validate_citations(result, make_chunks())


def test_reject_nonexistent_source():
    result = GroundedAnswer(
        answer="Approval is required.",
        sufficient_evidence=True,
        citations=[
            EvidenceCitation(
                reference=9,
                quote="Refunds above $500 require manager approval.",
            )
        ],
    )

    assert not validate_citations(result, make_chunks())


def test_reject_fabricated_quote():
    result = GroundedAnswer(
        answer="All refunds require approval.",
        sufficient_evidence=True,
        citations=[
            EvidenceCitation(
                reference=1,
                quote="All refunds require approval.",
            )
        ],
    )

    assert not validate_citations(result, make_chunks())


def test_reject_missing_citations():
    result = GroundedAnswer(
        answer="Refunds require approval.",
        sufficient_evidence=True,
        citations=[],
    )

    assert not validate_citations(result, make_chunks())
