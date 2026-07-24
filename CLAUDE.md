# Sentinel AI Development Instructions

This is the checked-in AI customization artifact. Claude Code reads it automatically; Codex, Copilot, and other coding agents should read it before modifying the repository.

## Purpose and impact

These instructions keep AI-assisted changes aligned with the required architecture. They prevent hardcoded answers, accidental cloud data exposure, lost citations, golden-dataset manipulation, and direct browser access to internal services. The coding agent used this context to preserve the exact stack, generate tests and documentation, review API contracts, and keep work isolated on feature branches. All generated changes remain subject to human review and automated tests.

## Required architecture

```text
React → authenticated .NET middleware → Python FastAPI RAG
             |                         → Weaviate + BGE + Ollama/Qwen
             └→ MongoDB persistence
```

Exact RAG path:

`Unstructured hi_res → title-aware chunks → BGE-small → Weaviate hybrid retrieval → BGE-reranker-v2-m3 → Ollama/Qwen3:4b`

## Repository map

- `rag/`: retrieval, reranking, generation, indexing, and abstention logic.
- `backend/app/`: FastAPI boundary and SSE contract; do not duplicate RAG logic here.
- `middleware/`: authentication, authorization, validation, proxying, MongoDB, and audit logs.
- `frontend/src/components/ui/`: reusable UI primitives.
- `frontend/src/features/`: feature-owned React components and state.
- `frontend/src/services/`: typed middleware API clients.
- `frontend/src/types/`: shared TypeScript contracts.
- `evaluation/`: golden data and evaluation reports.
- `tests/`: backend and RAG regression tests.

## Working rules

1. Keep documents and inference local unless the user explicitly changes that requirement.
2. Never hardcode RAG answers; improve retrieval, reranking, context selection, or prompting.
3. Preserve source, page, score, snippet, runtime, and safe-abstention metadata end-to-end.
4. The browser communicates only with .NET; never expose database or model credentials.
5. Validate conversation ownership for reads, writes, regeneration, version selection, and feedback.
6. Preserve SSE status, sources, token, persisted, done, and error events.
7. Use Radix UI, Tailwind, typed contracts, accessible labels, and visible success/error states.
8. Do not modify golden references merely to improve scores.
9. Never commit secrets, `.env`, model weights, `node_modules`, builds, or runtime logs.
10. Keep unrelated user changes untouched and work on a descriptive feature branch.

## Commands

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-full-stack.ps1
uv run python -m pytest tests/test_backend_streaming.py -q
dotnet test middleware/RagMiddleware.sln
cd frontend
npm run lint
npm run build
```

## Definition of done

- The happy path works through React → .NET → Python → MongoDB.
- Streaming, citations, regeneration, versions, feedback, and thread restore are verified.
- Python and .NET tests pass; frontend lint and production build pass.
- New errors have actionable UI feedback and safe server responses.
- README, report, and API documentation match the implementation.
- Changes are self-reviewed, meaningfully committed, pushed, and included in a PR.
