# Five-minute live demo

## Before presenting

1. Start Docker Desktop, Ollama, FastAPI, .NET, and React.
2. Open `http://127.0.0.1:5173`, sign in, and leave a clean new conversation selected.
3. Warm the exact pipeline once so model loading does not consume the demonstration.
4. Keep MongoDB `mongosh` open on the `sentinel` database.

## 0:00–0:30 — Introduce the value

Say: “Sentinel is a private CIS Controls assistant. Unlike a general chatbot, it retrieves from the supplied document, cites its evidence, abstains when evidence is missing, and stores feedback for continuous improvement.”

Show the exact-runtime badge and thread sidebar.

## 0:30–1:40 — Stream a grounded answer

Ask:

> Why are audit logs important? Format the answer as a short bullet list with bold keywords.

Point out the thinking state, token-by-token SSE rendering, Markdown bullets, and automatic scrolling. Say: “React sends the authenticated request to .NET. .NET proxies Python SSE. Python retrieves from Weaviate, reranks with BGE, and streams Qwen's grounded answer.”

## 1:40–2:20 — Prove grounding

Hover over `[1]`, click it, and expand **Sources & metadata**. Show the document, page, snippet, runtime, and latency.

Say: “The citation metadata travels with the retrieved evidence. The model does not invent the page reference.”

## 2:20–3:05 — Regenerate and version

Click **Regenerate**, wait for completion, and use the version selector to move between version 1 and version 2.

Say: “Regeneration creates an immutable response version rather than overwriting history. MongoDB stores the content, citations, runtime, and active version.”

## 3:05–3:45 — Demonstrate feedback

Click thumbs up and show the persistent highlight and toast. Then click thumbs down on another response, select a reason, add a short comment, and submit.

Say: “Feedback is tied to the conversation, message, and exact response version. That makes it actionable for evaluation rather than an anonymous count.”

## 3:45–4:20 — Demonstrate persistence

Refresh the browser. Reopen the same thread from the sidebar and show that messages and versions remain.

In `mongosh`, run:

```javascript
db.conversations.find().sort({ UpdatedAtUtc: -1 }).limit(1).pretty()
db.feedback.find().sort({ CreatedAtUtc: -1 }).limit(1).pretty()
```

Say: “React state is temporary; MongoDB persistence survives refreshes and service restarts.”

## 4:20–4:45 — Demonstrate safe abstention

Open a pre-warmed thread or ask:

> According to this document, what was the most common cyberattack in Lebanon in 2026?

Show the insufficient-evidence response. Say: “Qwen is pretrained, but the application configuration deliberately restricts answers to retrieved evidence.”

## 4:45–5:00 — Close with architecture and value

Say: “The key decision was using .NET as the security and persistence boundary while Python owns the RAG workflow. The business value is fast, private, auditable access to security knowledge, with a feedback loop that turns weak answers into measurable regression tests.”

## Recovery plan

- If Ollama is slow, show the pre-warmed thread and explain the recorded latency.
- If generation fails, show the safe extractive fallback and citations.
- If Docker is unavailable, use screenshots of the saved MongoDB conversation and feedback documents.
