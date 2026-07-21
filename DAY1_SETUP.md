# Day 1 — Backend and Frontend Foundation

## Delivered

- Dedicated FastAPI backend in `backend/app`
- Versioned API routes under `/api/v1`
- Vite + React + TypeScript frontend in `frontend`
- Tailwind CSS v4 through the Vite plugin
- Radix UI primitives and Lucide icons
- Feature-based frontend organization
- Git branch: `feature/frontend-setup`

## Structure

```text
backend/
  app/
    main.py          FastAPI lifecycle and routes
    schemas.py       Validated request contracts
frontend/
  src/
    components/ui/   Reusable visual primitives
    features/chat/   Sentinel chat feature
    services/        Typed backend client
    types/           Shared frontend contracts
```

## Run locally

Start Docker Desktop, Weaviate, and Ollama, then use two terminals.

```powershell
# Terminal 1 — API
cd C:\Projects\RAG_DAR
$env:RAG_RUNTIME="exact"
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — React
cd C:\Projects\RAG_DAR\frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. FastAPI documentation is available at
`http://127.0.0.1:8000/docs`.

## Verification

```powershell
uv run python -m unittest discover -s tests -v
cd frontend
npm run lint
npm run build
```
