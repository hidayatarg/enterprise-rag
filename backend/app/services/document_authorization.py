from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Document


class DocumentAuthorizationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def require_owned_document(
        self,
        document_id: UUID,
        user_id: UUID,
    ) -> Document:
        statement = select(Document).where(
            Document.id == document_id,
            Document.owner_id == user_id,
        )

        document = self.db.scalar(statement)

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found.",
            )

        return document
