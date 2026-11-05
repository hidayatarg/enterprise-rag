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