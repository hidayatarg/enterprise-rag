from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

class DocumentListItem(BaseModel):
    id: UUID
    filename: str
    content_type: str
    created_at: datetime
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


class DocumentDeleteResponse(BaseModel):
    document_id: UUID
    deleted: bool

class ChatResponse(BaseModel):
    answer: str
    model: str

class EmbeddingResponse(BaseModel):
    model: str
    dimensions: int
    preview: list[float]

class UploadResponse(BaseModel):
    document_id: UUID
    filename: str
    chunks_created: int
    status: str