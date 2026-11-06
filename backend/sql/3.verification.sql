-- ============================================
-- Enterprise RAG - Database Schema
-- Some verification queries to check the integrity of the database
-- ** Not required for the application to run, but useful for debugging and verification
-- ============================================

-- verify that your document vectors are stored correctly
SELECT
    d.id AS document_id,
    d.filename,
    COUNT(c.id) AS total_chunks
FROM documents d
LEFT JOIN document_chunks c
    ON c.document_id = d.id
GROUP BY d.id, d.filename
ORDER BY d.filename;


--verify vector dimensions
SELECT
    d.filename,
    c.chunk_index,
    c.page_number,
    vector_dims(c.embedding) AS dimensions
FROM document_chunks c
JOIN documents d
    ON d.id = c.document_id
LIMIT 10;