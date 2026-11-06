`Sample-policy.txt` will be used to test the RAG system. It contains a sample policy document that can be used to test the retrieval and question-answering capabilities of the system.



Start FastAPI

```bash
uvicorn app.main:app --reload --port 8000
uv run python -m uvicorn app.main:app --reload --port 8000
```

Synchronize dependencies

```bash
uv sync
```

Run tests
```bash
uv run python -m pytest tests/ -v
```