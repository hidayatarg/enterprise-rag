from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )

class EmbeddingRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=4000,
    )

class SearchRequest(BaseModel):
    document_id: UUID
    question: str = Field(
        min_length=1,
        max_length=4000,
    )
    top_k: int = Field(default=5, ge=1, le=20)