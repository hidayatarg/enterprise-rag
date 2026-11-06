# RAG service responsible for orchestrating the workflow
# It will coordinate three actions:
# 1. Embed the user's question.
# 2. Retrieve related chunks.
# 3. Generate an answer using the retrieved chunks.

from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.orm import Session
from app.ai_service import AIService
from app.retrieval_service import (RetrievedChunk, search_chunks)


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


def answer_document_question(
    db: Session,
    ai: AIService,
    document_id: UUID,
    question: str,
    top_k: int = 5,
) -> RAGResult:
    # Step 1: Generate the question embedding.
    vectors = ai.generate_embeddings([question])

    if len(vectors) != 1:
        raise ValueError("Invalid embedding response")

    query_vector = vectors[0]

    # Step 2: Retrieve relevant document chunks.
    chunks = search_chunks(
        db=db,
        query_vector=query_vector,
        document_id=document_id,
        limit=top_k,
    )

    # Step 3: Handle documents with no indexed chunks.
    if not chunks:
        return RAGResult(
            answer=(
                "I could not find this information "
                "in the provided document."
            ),
            sources=[],
            context_found=False,
        )

    # Step 4: Build numbered source context.
    context = build_context(chunks)

    # Step 5: Generate a grounded answer.
    answer = ai.generate_grounded_answer(
        question=question,
        context=context,
    )

    # Step 6: Return sources alongside the answer.
    sources = [
        {
            "reference": index,
            "filename": chunk.filename,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "similarity": chunk.similarity,
        }
        for index, chunk in enumerate(chunks, start=1)
    ]

    return RAGResult(
        answer=answer,
        sources=sources,
        context_found=True,
    )
