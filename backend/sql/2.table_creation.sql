
-- ============================================
-- Enterprise RAG - Database Schema
-- PostgreSQL + pgvector
-- ============================================

-- 1. Enable required extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;


-- 2. Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- 3. Document chunks table
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,

    CONSTRAINT fk_document_chunks_document
        FOREIGN KEY (document_id)
        REFERENCES documents(id)
        ON DELETE CASCADE,

    CONSTRAINT uq_document_chunk_index
        UNIQUE (document_id, chunk_index)
);


-- 4. Index for document lookup
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id
ON document_chunks(document_id);


-- 5. Index for vector similarity search
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding
ON document_chunks
USING hnsw (embedding vector_cosine_ops);
