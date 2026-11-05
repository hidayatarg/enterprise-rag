from uuid import UUID

from sqlalchemy.orm import Session

from app.ai_service import AIService
from app.document_processor import TextChunk
from app.models import Document, DocumentChunk


EMBEDDING_DIMENSIONS = 768
EMBEDDING_BATCH_SIZE = 16


def ingest_document(
    db: Session,
    ai: AIService,
    filename: str,
    content_type: str,
    chunks: list[TextChunk],
) -> tuple[UUID, int]:
    if not chunks:
        raise ValueError("Document has no text chunks")

    document = Document(
        filename=filename,
        content_type=content_type,
    )

    try:
        db.add(document)
        db.flush()

        for start in range(
            0,
            len(chunks),
            EMBEDDING_BATCH_SIZE,
        ):
            batch = chunks[
                start:start + EMBEDDING_BATCH_SIZE
            ]

            vectors = ai.generate_embeddings(
                [chunk.content for chunk in batch]
            )

            if len(vectors) != len(batch):
                raise ValueError(
                    "Embedding count does not match chunks"
                )

            for chunk, vector in zip(batch, vectors):
                if len(vector) != EMBEDDING_DIMENSIONS:
                    raise ValueError(
                        f"Expected {EMBEDDING_DIMENSIONS} "
                        f"dimensions, got {len(vector)}"
                    )

                db.add(
                    DocumentChunk(
                        document_id=document.id,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        content=chunk.content,
                        embedding=vector,
                    )
                )

        db.commit()

        return document.id, len(chunks)

    except Exception:
        db.rollback()
        raise
