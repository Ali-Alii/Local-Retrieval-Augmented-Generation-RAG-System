# Day 3 — Streaming Chat

## Delivered

- POST-based Server-Sent Events endpoint at `/api/v1/ask/stream`
- Real Qwen token streaming after exact retrieval and BGE reranking
- React message, input, phase, loading, error, and completion state
- Incremental SSE parsing with `status`, `token`, `done`, and `error` events
- Safe Markdown rendering using `react-markdown` and `remark-gfm`
- Retrieval and generation thinking indicators
- Automatic scroll-to-bottom as streamed tokens update the conversation

Persistence and interactive source citations remain intentionally deferred to the next task.
