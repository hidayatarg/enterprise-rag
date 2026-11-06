# Semantic Search

from dataclasses import dataclass
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Document, DocumentChunk


@dataclass(frozen=True) # Data transfer object containing the retrieved content and its source information
class RetrievedChunk:
    content: str
    filename: str
    page_number: int
    chunk_index: int
    distance: float

    @property
    def similarity(self) -> float: # Convert cosine distance to similarity score (1 - distance)
        return 1.0 - self.distance


def search_chunks(
    db: Session,
    query_vector: list[float],
    document_id: UUID,
    limit: int = 5,
) -> list[RetrievedChunk]:

    if len(query_vector) != 768:
        raise ValueError(
            "Expected a 768-dimensional query vector"
        )

    if not 1 <= limit <= 20:
        raise ValueError("limit must be between 1 and 20")

    # Pgvector cosine distance
    distance = (
        DocumentChunk.embedding
        .cosine_distance(query_vector) # SQLAlchemy's pgvector integration generates the PostgreSQL cosine-distance operation.
    )

    # Sql statement to retrieve document chunks ordered by similarity to the query vector
    statement = (
        select(
            DocumentChunk,
            Document.filename,
            distance.label("distance"),
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id,
        ) 
        .where( 
            DocumentChunk.document_id == document_id
        ) # Restricts search to one uploaded document 
          # In an enterprise application, we'd also verify the user's access to the document.
        .order_by(distance)
        .limit(limit)
    )

    rows = db.execute(statement).all()

    return [
        RetrievedChunk(
            content=chunk.content,
            filename=filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            distance=float(score),
        )
        for chunk, filename, score in rows
    ]
