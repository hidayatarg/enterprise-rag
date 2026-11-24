
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

-- 6. Users authentication table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Unique identifier for each user
    username VARCHAR(100) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    company VARCHAR(200),
    job_title VARCHAR(150),
    password_hash TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 7 Add owner_id column to documents table
BEGIN;

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS owner_id UUID;

CREATE INDEX IF NOT EXISTS idx_documents_owner_id
ON documents(owner_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_documents_owner'
          AND conrelid = 'documents'::regclass
    ) THEN
        ALTER TABLE documents
        ADD CONSTRAINT fk_documents_owner
        FOREIGN KEY (owner_id)
        REFERENCES users(id)
        ON DELETE RESTRICT;
    END IF;
END $$;

COMMIT;


8-- update the owner_id of document
SELECT id, filename, owner_id
    FROM documents;

SELECT id, username
    FROM users;

UPDATE documents
SET owner_id = 'YOUR_USER_UUID'
WHERE id = 'YOUR_DOCUMENT_UUID'
  AND owner_id IS NULL;