
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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
