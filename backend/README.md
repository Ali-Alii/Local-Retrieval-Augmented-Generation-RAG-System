# Sentinel Backend

FastAPI boundary around the existing local RAG engine.

```powershell
$env:RAG_RUNTIME="exact"
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Interactive API documentation: `http://127.0.0.1:8000/docs`.
