
import pytest
from pydantic import ValidationError

from app.rag_schemas import (
    EvidenceCitation,
    GroundedAnswer,
)


def test_valid_grounded_answer():
    result = GroundedAnswer(
        answer="Approved refunds take five business days.",
        sufficient_evidence=True,
        citations=[
            EvidenceCitation(
                reference=1,
                quote=(
                    "Approved refunds are processed "
                    "within 5 business days."
                ),
            )
        ],
    )

    assert result.sufficient_evidence is True
    assert len(result.citations) == 1


def test_valid_abstention():
    result = GroundedAnswer(
        answer="I could not find this information.",
        sufficient_evidence=False,
        citations=[],
    )

    assert result.sufficient_evidence is False
    assert result.citations == []


def test_reject_supported_answer_without_citations():
    with pytest.raises(
        ValidationError,
        match="Sufficient evidence requires",
    ):
        GroundedAnswer(
            answer="Refunds take five business days.",
            sufficient_evidence=True,
            citations=[],
        )


def test_reject_citations_when_evidence_insufficient():
    with pytest.raises(
        ValidationError,
        match="Insufficient evidence cannot",
    ):
        GroundedAnswer(
            answer="Information unavailable.",
            sufficient_evidence=False,
            citations=[
                EvidenceCitation(
                    reference=1,
                    quote="Refund policy",
                )
            ],
        )


def test_reject_invalid_citation_reference():
    with pytest.raises(ValidationError):
        EvidenceCitation(
            reference=0,
            quote="Refunds require approval.",
        )
