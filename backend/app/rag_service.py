# RAG service responsible for orchestrating the workflow
# It will coordinate three actions:
# 1. Embed the user's question.
# 2. Retrieve related chunks.
# 3. Generate an answer using the retrieved chunks.

# Updates
#  Retrieve ---> Filter irrelevant chunks ---> Screen for obvious injection patterns 
# ---> Generate structured response ---> Validate citations references ----> Validate exact evidence quotations 
# ---> Return answer or abstain

from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.orm import Session
from app.ai_service import AIService
from app.retrieval_service import RetrievedChunk, search_chunks
from app.citation_validator import validate_citations
from app.security import contains_prompt_injection


ABSTAIN = (
    "I could not find this information "
    "in the provided document."
)


@dataclass(frozen=True)
class RAGResult:
    answer: str
    sources: list[dict]
    context_found: bool


def build_context(chunks: list[RetrievedChunk]) -> str:
    sections = []

    for index, chunk in enumerate(chunks, start=1):
        sections.append(
            f"[{index}]\n"
            f"File: {chunk.filename}\n"
            f"Page: {chunk.page_number}\n"
            f"Content:\n{chunk.content}"
        )

    return "\n\n".join(sections)


def abstain() -> RAGResult:
    return RAGResult(
        answer=ABSTAIN,
        sources=[],
        context_found=False,
    )

def answer_document_question(
    db: Session,
    ai: AIService,
    document_id: UUID,
    question: str,
    top_k: int = 5,
) -> RAGResult:

    # 1. Generate question embedding
    vectors = ai.generate_embeddings([question])

    if len(vectors) != 1 or len(vectors[0]) != 768:
        raise ValueError("Invalid embedding response")

    # 2. Search PostgreSQL with relevance filtering
    chunks = search_chunks(
        db=db,
        query_vector=vectors[0],
        document_id=document_id,
        limit=top_k,
        min_similarity=0.45,
    )

    if not chunks:
        return abstain()

    # 3. Screen retrieved chunks.
    # This is a limited heuristic, not complete protection.
    safe_chunks = [
        chunk for chunk in chunks
        if not contains_prompt_injection(chunk.content)
    ]

    if not safe_chunks:
        return abstain()

    # Limit the context sent to the LLM.
    safe_chunks = safe_chunks[:5]

    context = build_context(safe_chunks)

    # 4. Generate structured answer
    generated = ai.generate_grounded_answer(
        question=question,
        context=context,
    )

    if not generated.sufficient_evidence:
        return abstain()

    # 5. Validate citation references and quotes
    if not validate_citations(generated, safe_chunks):
        return abstain()

    # 6. Return only cited source records
    cited_refs = {
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
        for index, chunk in enumerate(safe_chunks, start=1)
        if index in cited_refs
    ]

    return RAGResult(
        answer=generated.answer,
        sources=sources,
        context_found=True,
    )
