"""
RAG Service — Retrieval-Augmented Generation Orchestrator

Workflow:
1. Generate a question embedding using Ollama.
2. Retrieve semantically relevant chunks from PostgreSQL.
3. Filter chunks using a similarity threshold.
4. Screen chunks for obvious prompt injection.
5. Build numbered context for the LLM.
6. Generate a structured answer using Llama.
7. Check whether the model considers evidence sufficient.
8. Validate citation references and exact quotations.
9. Return the grounded answer or abstain.

Note:
The injection detector and citation validator are initial
defenses, not guarantees of security or factual correctness.
"""

import logging
from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.orm import Session
from app.ai_service import AIService
from app.retrieval_service import RetrievedChunk, search_chunks
from app.citation_validator import validate_citations
from app.security import contains_prompt_injection


logger = logging.getLogger(__name__)

# Enable detailed diagnostics only for synthetic test data.
# Set to False after debugging.
DEBUG_RAG = False

EMBEDDING_DIMENSIONS = 768
MIN_SIMILARITY = 0.45
MAX_CONTEXT_CHUNKS = 5

ABSTAIN_MESSAGE = (
    "I could not find this information "
    "in the provided document."
)


@dataclass(frozen=True)
class RAGResult:
    answer: str
    sources: list[dict]
    context_found: bool


def build_context(chunks: list[RetrievedChunk]) -> str:
    """
    Convert retrieved chunks into numbered context.

    Example:

    [1]
    File: sample-policy.txt
    Page: 1
    Content:
    Approved refunds are processed within 5 business days.
    """

    sections = []

    for index, chunk in enumerate(chunks, start=1):
        sections.append(
            f"[{index}]\n"
            f"File: {chunk.filename}\n"
            f"Page: {chunk.page_number}\n"
            f"Content:\n{chunk.content}"
        )

    return "\n\n".join(sections)


def abstain(
    context_found: bool = False,
    reason: str = "UNKNOWN",
) -> RAGResult:
    """
    Return a safe abstention response.

    context_found indicates whether relevant chunks were
    available, not whether Llama produced a valid answer.
    """

    logger.warning("RAG abstention: %s", reason)

    return RAGResult(
        answer=ABSTAIN_MESSAGE,
        sources=[],
        context_found=context_found,
    )

def answer_document_question(
    db: Session,
    ai: AIService,
    document_id: UUID,
    question: str,
    top_k: int = 5,
) -> RAGResult:
    """
    Execute the complete RAG pipeline.
    """

    logger.info(
        "RAG started: document_id=%s top_k=%s",
        document_id,
        top_k,
    )

    # ==================================================
    # STEP 1 — Generate question embedding
    # ==================================================

    vectors = ai.generate_embeddings([question])

    if (
        len(vectors) != 1
        or len(vectors[0]) != EMBEDDING_DIMENSIONS
    ):
        logger.error(
            "Invalid embedding response: count=%d",
            len(vectors),
        )
        raise ValueError("Invalid embedding response")

    query_vector = vectors[0]

    logger.info(
        "RAG embedding generated: dimensions=%d",
        len(query_vector),
    )

    # ==================================================
    # STEP 2 — Retrieve relevant chunks
    # ==================================================

    chunks = search_chunks(
        db=db,
        query_vector=query_vector,
        document_id=document_id,
        limit=top_k,
        min_similarity=MIN_SIMILARITY,
    )

    logger.info(
        "RAG retrieval: chunks=%d similarities=%s",
        len(chunks),
        [round(chunk.similarity, 4) for chunk in chunks],
    )

    if not chunks:
        return abstain(
            context_found=False,
            reason="NO_RELEVANT_CHUNKS",
        )

    # ==================================================
    # STEP 3 — Screen prompt injection
    # ==================================================

    safe_chunks = [
        chunk
        for chunk in chunks
        if not contains_prompt_injection(chunk.content)
    ]

    logger.info(
        "RAG security screening: retrieved=%d accepted=%d",
        len(chunks),
        len(safe_chunks),
    )

    if not safe_chunks:
        return abstain(
            context_found=True,
            reason="ALL_CHUNKS_SCREENED",
        )

    # Limit the amount of retrieved content.
    safe_chunks = safe_chunks[:MAX_CONTEXT_CHUNKS]

    # ==================================================
    # STEP 4 — Build numbered context
    # ==================================================

    context = build_context(safe_chunks)

    logger.info(
        "RAG context prepared: chunks=%d characters=%d",
        len(safe_chunks),
        len(context),
    )

    if DEBUG_RAG:
        # Only enable with synthetic/non-sensitive data.
        logger.warning(
            "RAG DEBUG — Context sent to Llama:\n%s",
            context,
        )

    # ==================================================
    # STEP 5 — Generate structured answer
    # ==================================================

    generated = ai.generate_grounded_answer(
        question=question,
        context=context,
    )

    logger.warning(
        "RAG DEBUG — sufficient_evidence=%s | "
        "citations=%d | answer=%s",
        generated.sufficient_evidence,
        len(generated.citations),
        generated.answer if DEBUG_RAG else "[REDACTED]",
    )

    if DEBUG_RAG:
        logger.warning(
            "RAG DEBUG — Citation details: %s",
            [
                {
                    "reference": citation.reference,
                    "quote": citation.quote,
                }
                for citation in generated.citations
            ],
        )

    # ==================================================
    # STEP 6 — Check evidence sufficiency
    # ==================================================

    if not generated.sufficient_evidence:
        return abstain(
            context_found=True,
            reason="MODEL_INSUFFICIENT_EVIDENCE",
        )

    # A supported answer must include citations.
    if not generated.citations:
        return abstain(
            context_found=True,
            reason="MODEL_MISSING_CITATIONS",
        )

    # ==================================================
    # STEP 7 — Validate source citations
    # ==================================================

    citations_valid = validate_citations(
        generated,
        safe_chunks,
    )

    logger.info(
        "RAG citation validation: valid=%s",
        citations_valid,
    )

    if not citations_valid:
        return abstain(
            context_found=True,
            reason="CITATION_VALIDATION_FAILED",
        )

    # ==================================================
    # STEP 8 — Return cited sources
    # ==================================================

    cited_references = {
        citation.reference
        for citation in generated.citations
    }

    sources = [
        {
            "reference": index,
            "filename": chunk.filename,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "similarity": chunk.similarity,
        }
        for index, chunk in enumerate(
            safe_chunks,
            start=1,
        )
        if index in cited_references
    ]

    logger.info(
        "RAG completed successfully: citations=%d",
        len(sources),
    )

    return RAGResult(
        answer=generated.answer,
        sources=sources,
        context_found=True,
    )
