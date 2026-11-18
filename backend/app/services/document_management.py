from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

# Adapt these imports to your existing project structure.
from app.models.models import Document, DocumentChunk

# list documents with their chunk counts
def list_documents(db: Session):
    statement = (
        select(
            Document.id,
            Document.filename,
            Document.content_type,
            Document.created_at,
            func.count(DocumentChunk.id).label("chunk_count"),
        )
        .outerjoin(
            DocumentChunk,
            DocumentChunk.document_id == Document.id,
        )
        .group_by(
            Document.id,
            Document.filename,
            Document.content_type,
            Document.created_at,
        )
        .order_by(Document.created_at.desc(), Document.id.desc())
    )

    return db.execute(statement).mappings().all()


# delete a document and its associated chunks
def delete_document(db: Session, document_id: UUID) -> bool:
    document = db.get(Document, document_id)

    if document is None:
        return False

    # Explicitly remove child rows so deletion works even
    # if the FK does not have ON DELETE CASCADE.
    db.execute(
        delete(DocumentChunk).where(
            DocumentChunk.document_id == document_id
        )
    )

    db.delete(document)
    db.commit()

    return True
