CREATE EXTENSION IF NOT EXISTS vector;

SELECT extname, extversion
FROM pg_extension
WHERE extname = 'vector';

CREATE TABLE learning_vectors (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(3) NOT NULL
);

SELECT * from learning_vectors 


INSERT INTO learning_vectors (content, embedding)
VALUES
    ('Payment transaction', '[0.9, 0.1, 0.1]'),
    ('Refund transaction',  '[0.8, 0.2, 0.1]'),
    ('Weather forecast',    '[0.1, 0.1, 0.9]');

-- execute your first similarity search:
SELECT
    content,
    ROUND(
        (embedding <=> '[0.85, 0.15, 0.1]')::numeric,
        4
    ) AS cosine_distance
FROM learning_vectors
ORDER BY embedding <=> '[0.85, 0.15, 0.1]'
LIMIT 3;
