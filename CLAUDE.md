# Sentinel AI Development Instructions

This file gives AI coding assistants the project context, commands, boundaries, and quality checks required to work safely in this repository. Claude Code can read it automatically; other assistants should read it before making changes.

## Project purpose

Sentinel is a fully local CIS Controls v8 RAG application. Preserve the exact pipeline:

`Unstructured hi_res → title chunks → BGE-small → Weaviate → BGE-reranker-v2-m3 → Ollama/Qwen3:4b`

## Repository map

- `rag/`: existing retrieval, reranking, generation, and indexing logic
- `backend/app/`: FastAPI boundary; do not duplicate RAG logic here
- `frontend/src/components/ui/`: reusable UI primitives
- `frontend/src/features/`: feature-owned components and state
- `frontend/src/services/`: typed API clients
- `frontend/src/types/`: shared TypeScript contracts
- `evaluation/`: golden data and evaluation reports
- `tests/`: backend and RAG regression tests

## Working rules

1. Keep documents and model inference local.
2. Never hardcode final RAG answers; improve retrieval or prompting instead.
3. Preserve source page metadata and safe abstention.
4. Use the versioned `/api/v1` contract.
5. Use Radix UI primitives and Tailwind consistently.
6. Do not add streaming until the dedicated streaming task.
7. Do not modify golden references merely to improve scores.
8. Do not commit `.env`, model files, `node_modules`, or generated builds.

## Commands

```powershell
# Backend
uv sync
$env:RAG_RUNTIME="exact"
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend
cd frontend
npm install
npm run dev

# Verification
uv run python -m unittest discover -s tests -v
cd frontend
npm run lint
npm run build
```

## Definition of done

- Existing and new tests pass.
- Frontend lint and production build pass.
- API health and CORS connectivity are verified.
- Changes stay on the assigned feature branch.
- Documentation reflects new commands or architecture.
