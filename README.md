# Sentinel — Local CIS Controls RAG

Sentinel is a private, source-grounded cybersecurity assistant for CIS Controls v8. It combines an exact local RAG pipeline with a production-style React, .NET, MongoDB, and SSE application. Answers stream into the browser, cite the source PDF, abstain when evidence is missing, persist across refreshes, support regeneration and version history, and collect structured human feedback.

## What was shipped

- Exact RAG: Unstructured `hi_res`, title-aware chunks, BGE embeddings, Weaviate hybrid retrieval, BGE reranking, and Qwen3:4b through Ollama.
- React 19 chat UI with Markdown, loading states, token streaming, automatic scrolling, and a guided tour.
- Authenticated .NET 9 middleware with secure cookies, rate limiting, audit logs, safe errors, and Swagger.
- MongoDB persistence for users, sessions, conversations, response versions, feedback, and audit events.
- Clickable inline citations, snippet tooltips, and collapsible source metadata.
- Regeneration, version switching, thumbs up/down feedback, and reasoned negative feedback.
- A 20-question golden dataset with deterministic retrieval metrics and local DeepEval judging.

## Architecture

```text
Browser / React :5173
        |
        | authenticated REST + SSE
        v
.NET middleware :5100 ----------------> MongoDB :27017
        |                                conversations, feedback, sessions
        | protected upstream request
        v
Python FastAPI :8000
        |
        +--> Weaviate :8080 (332 vectors × 384 dimensions)
        +--> BGE reranker
        +--> Ollama :11434 --> Qwen3:4b
```

The browser never calls Python, MongoDB, Weaviate, or Ollama directly. The .NET middleware owns authentication, validation, persistence, and the public API boundary.

## Five-minute local setup

### Prerequisites

- Windows PowerShell 7+, Python 3.12, `uv`, Node.js 20+, .NET SDK 9+, and Docker Desktop.
- Ollama with `qwen3:4b` downloaded: `ollama pull qwen3:4b`.

```powershell
git clone https://github.com/Ali-Alii/Local-Retrieval-Augmented-Generation-RAG-System.git
cd Local-Retrieval-Augmented-Generation-RAG-System
git switch feature/day4-persistence-feedback
powershell -ExecutionPolicy Bypass -File scripts/start-full-stack.ps1
```

Open `http://127.0.0.1:5173` and choose **Local demo login**. The launcher installs locked dependencies, starts MongoDB and Weaviate, initializes the supplied 332-chunk exact index, and opens the Python, .NET, and React processes. First-time model downloads are excluded from the five-minute target and depend on internet speed. Later runs can use `-SkipInstall -SkipIndex`.

Stop the three spawned terminals and run `docker compose stop` to stop the databases.

### Manual startup

Open four PowerShell terminals from the repository root:

```powershell
docker compose up -d mongodb weaviate
uv sync --python 3.12
uv run python -m rag.exact_pipeline weaviate
```

```powershell
$env:RAG_RUNTIME="exact"
uv run python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```powershell
$env:Jwt__SigningKey="local-development-key-change-before-production-2026"
$env:Mongo__ConnectionString="mongodb://127.0.0.1:27017"
$env:Authentication__EnableDevelopmentLogin="true"
dotnet run --project middleware/src/RagMiddleware.Api --urls http://127.0.0.1:5100
```

```powershell
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

Health endpoints: Python `http://127.0.0.1:8000/api/v1/health`, middleware `http://127.0.0.1:5100/health`, Swagger `http://127.0.0.1:5100/swagger`.

## Exact RAG data flow

```text
CIS PDF → Unstructured hi_res → title-aware chunks → BGE-small embeddings → Weaviate
Question → BM25 + BGE hybrid retrieval → BGE reranker → grounded prompt → Qwen → cited answer
```

The verified ingestion extracted **2,655 elements** from **82 PDF pages**. Title-aware chunking produced **332 chunks** and **332 vectors × 384 dimensions**. A smaller reversible runtime contains 127 chunks for low-resource demonstrations, but the assignment and final evaluation use the exact stack.

## Evaluation

The golden dataset contains 20 direct, paraphrased, scenario, and abstention questions. Retrieval achieved 100% Hit@5 and 0.95 MRR@5. The final exact-stack DeepEval run completed 92 judgments with a **97.83% overall pass rate**: 100% answer relevancy, 94.44% faithfulness, 100% contextual relevancy, 100% contextual precision, 94.44% contextual recall, and 100% safe-abstention pass rates.

The golden dataset is the repeatable exam and answer key; DeepEval is the grading framework; local Qwen3:4b is the LLM judge. Deterministic metrics remain alongside judge metrics so a small judge model is never the only quality signal. See [`evaluation/DEEPEVAL_REPORT.md`](evaluation/DEEPEVAL_REPORT.md).

## Verification

```powershell
uv run python -m pytest tests/test_backend_streaming.py -q
dotnet test middleware/RagMiddleware.sln
cd frontend
npm run lint
npm run build
```

Full acceptance flow: login → create thread → ask a grounded question → watch SSE tokens → inspect citations → regenerate → switch versions → rate the answer → refresh → resume the saved conversation.

## Repository guide

- `rag/`: parsing, chunking, retrieval, reranking, generation, and exact runtime.
- `backend/app/`: FastAPI and Python SSE contract.
- `middleware/`: .NET security, proxy, persistence, and feedback boundary.
- `frontend/`: React application and feature components.
- `evaluation/`: golden dataset, deterministic evaluation, and DeepEval reports.
- `docs/FINAL_REPORT.md`: objectives, decisions, challenges, lessons, and business value.
- `docs/FINAL_SLIDES.md`: final three-slide content.
- `docs/LIVE_DEMO.md`: timed five-minute demonstration script.
- `CLAUDE.md`: checked-in AI coding-agent instructions and quality boundaries.

## Security and limitations

- Local development uses a development-only signing key and unauthenticated localhost databases. Use HTTPS, secret storage, authenticated MongoDB/Weaviate, and real OAuth in production.
- Unsupported or time-sensitive questions abstain rather than inventing evidence.
- A 20-question golden set demonstrates repeatability; it does not prove universal cybersecurity accuracy.
- Operators should inspect cited pages before making consequential security decisions.
