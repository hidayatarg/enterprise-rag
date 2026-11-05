
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import httpx
import ollama

from app.ai_service import AIService, get_ai_service


from app.database import get_db

app = FastAPI(
    title="Enterprise RAG API",
    description="Building RAG applications for enterprises with vector databases and LLMs",
    version="0.1.0",
)

DbSession = Annotated[Session, Depends(get_db)]

# Check FastAPI is running
@app.get("/api/v1/health")
def health():
    return {
        "status": "healthy",
        "service": "enterprise-rag-api",
    }

# Check database connection and pgvector extension
@app.get("/api/v1/database/status")
def database_status(db: DbSession):
    try:
        result = db.execute(
            text("""
                SELECT extversion
                FROM pg_extension
                WHERE extname = 'vector'
            """)
        ).scalar_one_or_none()

        if result is None:
            raise HTTPException(
                status_code=503,
                detail="pgvector extension is not enabled",
            )

        return {
            "status": "connected",
            "database": "PostgreSQL",
            "pgvector_version": result,
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )


@app.get("/api/v1/vectors")
def list_vectors(db: DbSession):
    try:
        rows = db.execute(
            text("""
                SELECT
                    id,
                    content,
                    CAST(embedding AS TEXT) AS embedding
                FROM learning_vectors
                ORDER BY id
            """)
        ).mappings().all()

        return {
            "count": len(rows),
            "items": [dict(row) for row in rows],
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve vectors",
        )


class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
    )


class ChatResponse(BaseModel):
    answer: str
    model: str


class EmbeddingRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=4000,
    )


class EmbeddingResponse(BaseModel):
    model: str
    dimensions: int
    preview: list[float]


AI = Annotated[AIService, Depends(get_ai_service)]

@app.post("/api/v1/ai/chat", response_model=ChatResponse)
def chat(request: ChatRequest, ai: AI):
    try:
        answer = ai.generate_answer(request.question)

        return ChatResponse(
            answer=answer,
            model=ai.chat_model,
        )
    except (ollama.ResponseError, httpx.HTTPError, OSError):
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable",
        )


@app.post("/api/v1/ai/embed", response_model=EmbeddingResponse)
def embed_text(request: EmbeddingRequest, ai: AI):
    try:
        vectors = ai.generate_embeddings(
            [request.text]
        )

        vector = vectors[0]

        return EmbeddingResponse(
            model=ai.embedding_model,
            dimensions=len(vector),
            preview=vector[:5], # Return the first 5 dimensions of the embedding vector for debugging
        )
    except (ollama.ResponseError, httpx.HTTPError, OSError):
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable",
        )
