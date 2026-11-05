... Under development, this project is a template for building RAG applications for enterprises with vector databases and LLMs. It uses the following architecture:


React + FastAPI + PostgreSQL/pgvector + Ollama RAG architecture


SQLAlchemy handles sessions, connections, pooling, transaction management, and optional ORM mapping. PostgreSQL still executes our actual SQL statements.


RAG requires document ingestion, embeddings, vector retrieval, and an LLM.

![alt text](img/image.png)