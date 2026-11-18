from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True) # It will tell users how many searchable chunks were generated for each document..

    id: UUID
    filename: str
    content_type: str
    created_at: datetime
    chunk_count: int = Field(ge=0) # This field represents the number of chunks associated with the document.


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


class DocumentDeleteResponse(BaseModel):
    document_id: UUID
    deleted: bool
