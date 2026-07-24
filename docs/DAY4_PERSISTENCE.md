# Day 4: Persistence and feedback

## What was added

- MongoDB conversations containing user and assistant messages.
- Immutable assistant response versions for regeneration and version switching.
- A React thread list that restores past chats after refresh.
- Inline clickable citations, snippet tooltips, and a source metadata accordion.
- Positive feedback and required-reason negative feedback persisted in MongoDB.
- A three-step first-use guided tour stored only as a browser completion preference.

## Request flow

```text
React creates/selects conversation
  -> POST .NET /api/rag/query/stream
  -> .NET proxies Python SSE status, sources, and tokens
  -> Python retrieves with Weaviate + BGE and generates with Qwen/Ollama
  -> .NET stores the completed response and source metadata in MongoDB
  -> .NET emits a persisted event followed by done
  -> React reloads the canonical conversation from MongoDB
```

The browser talks only to the authenticated .NET middleware. Conversation ownership is checked on every load, stream, version change, and feedback request.

## Run all services

Open separate PowerShell terminals from the repository root:

```powershell
docker compose up -d mongodb weaviate
```

```powershell
$env:RAG_RUNTIME="exact"
uv run python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```powershell
dotnet run --project middleware/src/RagMiddleware.Api --urls http://127.0.0.1:5100
```

```powershell
cd frontend
npm run dev
```

Open `http://127.0.0.1:5173`. For a local demo, enable the development login as documented in `middleware/README.md`.

## Manual acceptance test

1. Sign in and create a new chat.
2. Ask a grounded CIS question and watch the answer stream.
3. Click an inline citation and inspect its tooltip and source accordion.
4. Refresh the page and confirm the same thread and answer return.
5. Regenerate the answer and switch between version 1 and version 2.
6. Submit thumbs up, then thumbs down with a reason and optional comment.
7. Create another thread and switch between both threads.

## Verified checks

- React lint and production build pass.
- .NET solution builds with zero warnings and zero errors.
- Conversation create/save/reload returns two persisted messages.
- Regeneration stores two versions and active-version switching persists.
- Negative feedback returns a persisted MongoDB feedback identifier.
- An exact-stack grounded query stored three citation sources including page metadata.
