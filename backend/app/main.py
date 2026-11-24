from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import ValidationError
import httpx
import ollama

from pathlib import Path
from uuid import UUID
import pymupdf

from app.document_processor import process_document
from app.services.ingestion_service import ingest_document

from app.services.ai_service import AIService, get_ai_service

from app.database import get_db
from app.services.retrieval_service import search_chunks
from app.services.rag_service import answer_document_question
from app.models.responses import DocumentListItem, DocumentListResponse, DocumentDeleteResponse, ChatResponse, EmbeddingResponse, UploadResponse
from app.models.requests import ChatRequest, EmbeddingRequest, SearchRequest

from app.schemas.auth_schemas import UserRegisterRequest, UserResponse, TokenResponse, UserLoginRequest
from app.services.user_service import UserService, UsernameAlreadyExistsError, InvalidCredentialsError
from app.services.jwt_service import JWTService
from app.models.models import User
from app.services.auth_dependencies import get_current_user

from app.services.document_authorization import DocumentAuthorizationService

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


@app.post("/api/v1/documents/upload", response_model=UploadResponse, status_code=201)
def upload_document(
    db: DbSession,
    ai: AI,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
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
            owner_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except (ollama.ResponseError, httpx.HTTPError, OSError):
        raise HTTPException(
            status_code=503,
            detail="Embedding service unavailable",
        ) from None
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from None

    return UploadResponse(
        document_id=document_id,
        filename=filename,
        chunks_created=count,
        status="indexed",
    )


# Retrieve matching document chunks
@app.post("/api/v1/documents/search")
def search_document(request: SearchRequest, db: DbSession, ai: AI,
    current_user: User = Depends(get_current_user),
):
    try:
        # 1. Verify document ownership before retrieval.
        DocumentAuthorizationService(db).require_owned_document(
            document_id=request.document_id,
            user_id=current_user.id,
        )

        # 2. Generate question embedding.
        query_vector = ai.generate_embeddings(
            [request.question]
        )[0]

        # 3. Search the authenticated user's document.
        chunks = search_chunks(
            db=db,
            query_vector=query_vector,
            document_id=request.document_id,
            limit=request.top_k,
        )

        # 4. Return matching chunks.
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
        ) from None

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from None

    except (ValueError, IndexError):
        raise HTTPException(
            status_code=502,
            detail="Invalid embedding response",
        ) from None


# Retrieve chunks and generate an answer with Llama
@app.post("/api/v1/documents/ask")
def ask_document(request: SearchRequest, db: DbSession, ai: AI,
    current_user: User = Depends(get_current_user),
):
    try:
        # Verify document ownership before retrieval.
        DocumentAuthorizationService(db).require_owned_document(
            document_id=request.document_id,
            user_id=current_user.id,
        )

        # Run the existing RAG pipeline only after authorization.
        result = answer_document_question(
            db=db,
            ai=ai,
            document_id=request.document_id,
            question=request.question,
            top_k=request.top_k,
        )

        return {
            "question": request.question,
            "answer": result.answer,
            "context_found": result.context_found,
            "sources": result.sources,
        }

    except (ollama.ResponseError, httpx.HTTPError, OSError):
        raise HTTPException(
            status_code=503,
            detail="AI service unavailable",
        ) from None

    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        ) from None

    except (ValueError, IndexError, ValidationError):
        raise HTTPException(
            status_code=502,
            detail="Invalid retrieval or model response",
        ) from None


# List documents with their chunk counts
@app.get("/api/v1/documents", response_model=DocumentListResponse)
def list_documents(db: DbSession):
    try:
        rows = db.execute(
            text("""
                SELECT
                    d.id,
                    d.filename,
                    d.content_type,
                    d.created_at,
                    COUNT(c.id) AS chunk_count
                FROM documents d
                LEFT JOIN document_chunks c
                    ON c.document_id = d.id
                GROUP BY
                    d.id,
                    d.filename,
                    d.content_type,
                    d.created_at
                ORDER BY
                    d.created_at DESC,
                    d.id DESC
            """)
        ).mappings().all()

        documents = [
            DocumentListItem.model_validate(dict(row))
            for row in rows
        ]

        return DocumentListResponse(
            documents=documents,
            total=len(documents),
        )

    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to retrieve documents",
        ) from exc


# Delete a document and its associated chunks
@app.delete("/api/v1/documents/{document_id}", response_model=DocumentDeleteResponse)
def delete_document(document_id: UUID, db: DbSession):
    try:
        # Delete all indexed chunks belonging to the document.
        db.execute(
            text("""
                DELETE FROM document_chunks
                WHERE document_id = :document_id
            """),
            {"document_id": document_id},
        )

        # Delete the document itself.
        result = db.execute(
            text("""
                DELETE FROM documents
                WHERE id = :document_id
                RETURNING id
            """),
            {"document_id": document_id},
        )

        deleted_id = result.scalar_one_or_none()

        if deleted_id is None:
            db.rollback()

            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        db.commit()

        return DocumentDeleteResponse(
            document_id=deleted_id,
            deleted=True,
        )

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Unable to delete document",
        ) from exc


@app.post("/api/v1/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
def register_user(
    request: UserRegisterRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    service = UserService(db)

    try:
        user = service.register_user(request)
    except UsernameAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username is already registered.",
        ) from None

    return UserResponse.model_validate(user)


@app.post("/api/v1/auth/login", response_model=TokenResponse,
    tags=["Authentication"],
)
def login_user(
    request: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    service = UserService(db)

    try:
        user = service.authenticate_user(
            username=request.username,
            password=request.password,
        )
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    jwt_service = JWTService()

    access_token = jwt_service.create_access_token(
        user.id
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=jwt_service.expiration_minutes * 60,
        user=UserResponse.model_validate(user),
    )

@app.get("/api/v1/auth/me", response_model=UserResponse,
    tags=["Authentication"],
)
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)