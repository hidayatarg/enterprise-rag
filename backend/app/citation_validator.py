import re

from app.rag_schemas import GroundedAnswer
from app.retrieval_service import RetrievedChunk


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def validate_citations(result: GroundedAnswer, chunks: list[RetrievedChunk]) -> bool:

    if not result.sufficient_evidence:
        return False

    if not result.answer.strip():
        return False

    if not result.citations:
        return False

    for citation in result.citations:
        index = citation.reference - 1

        # Citation number must exist.
        if index < 0 or index >= len(chunks):
            return False

        source = normalize_text(
            chunks[index].content
        )

        quote = normalize_text(
            citation.quote
        )

        # Quote must exist in the cited source.
        if quote not in source:
            return False

    return True
