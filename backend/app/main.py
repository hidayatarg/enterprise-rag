from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, File, UploadFile
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import httpx
import ollama

from pathlib import Path
from uuid import UUID
import pymupdf

from app.document_processor import process_document
from app.ingestion_service import ingest_document

from app.ai_service import AIService, get_ai_service

from app.database import get_db
from app.retrieval_service import search_chunks

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


MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_CHUNKS = 100


class UploadResponse(BaseModel):
    document_id: UUID
    filename: str
    chunks_created: int
    status: str


@app.post("/api/v1/documents/upload", response_model=UploadResponse, status_code=201)
def upload_document(
    db: DbSession,
    ai: AI,
    file: UploadFile = File(...),
):
    filename = Path(file.filename or "").name

    extension = Path(filename).suffix.lower()

    if extension not in {".pdf", ".txt"}:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are supported",
        )

    data = file.file.read(MAX_FILE_SIZE + 1)

    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds 5 MB limit",
        )

    if not data:
        raise HTTPException(
            status_code=400,
            detail="Empty file",
        )

    try:
        chunks = process_document(data, filename)
    except (ValueError, UnicodeDecodeError, pymupdf.FileDataError):
        raise HTTPException(
            status_code=400,
            detail="Unable to extract document text",
        )

    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="No extractable text found",
        )

    if len(chunks) > MAX_CHUNKS:
        raise HTTPException(
            status_code=413,
            detail="Document exceeds chunk limit",
        )

    try:
        document_id, count = ingest_document(
            db=db,
            ai=ai,
            filename=filename,
            content_type=(
                "application/pdf"
                if extension == ".pdf"
                else "text/plain"
            ),
            chunks=chunks,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )
    except (ollama.ResponseError, httpx.HTTPError, OSError):
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable",
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

    return UploadResponse(
        document_id=document_id,
        filename=filename,
        chunks_created=count,
        status="indexed",
    )


class SearchRequest(BaseModel):
    document_id: UUID
    question: str = Field(
        min_length=1,
        max_length=4000,
    )
    top_k: int = Field(default=5, ge=1, le=20)


@app.post("/api/v1/documents/search")
def search_document(request: SearchRequest, db: DbSession, ai: AI):
    try:
        query_vector = ai.generate_embeddings(
            [request.question]
        )[0]

        chunks = search_chunks(
            db=db,
            query_vector=query_vector,
            document_id=request.document_id,
            limit=request.top_k,
        )

        return {
            "question": request.question,
            "results": [
                {
                    "content": chunk.content,
                    "filename": chunk.filename,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "distance": chunk.distance,
                    "similarity": chunk.similarity,
                }
                for chunk in chunks
            ],
        }

    except (ollama.ResponseError, httpx.HTTPError, OSError):
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable",
        )

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )

    except (ValueError, IndexError):
        raise HTTPException(
            status_code=502,
            detail="Invalid embedding response",
        )

