# Sentinel — Final three-slide deck

## Slide 1 — From assignment to shipped product

**Asked:** build a local CIS Controls RAG pipeline, connect a frontend, stream responses, persist chats, expose citations, and collect feedback.

**Shipped:** a private full-stack cybersecurity workspace with grounded SSE answers, safe abstention, clickable evidence, MongoDB thread history, regeneration/versioning, structured feedback, authentication, evaluation, and onboarding.

**Stack:** React 19 + TypeScript + Tailwind + Radix UI | .NET 9 middleware | Python/FastAPI | Unstructured | BGE-small | Weaviate | BGE reranker | Ollama/Qwen3:4b | MongoDB | DeepEval.

**Proof:** 82 pages → 2,655 elements → 332 chunks/vectors; 20 golden questions; 100% Hit@5; 0.95 MRR@5; 97.83% overall DeepEval pass rate.

## Slide 2 — Architecture and grounded AI flow

```text
React --authenticated REST/SSE--> .NET middleware ----> MongoDB
                                      |
                                      v
                                  FastAPI RAG
                                      |
PDF → Unstructured → BGE → Weaviate hybrid → BGE rerank → Qwen/Ollama
                                      |
                                answer + [citations]
```

**Justified decision:** .NET is the security and persistence boundary. The browser cannot reach Python, MongoDB, Weaviate, or Ollama directly. Python remains optimized for ML experimentation; .NET owns authentication, validation, conversation ownership, feedback, auditing, and stable APIs.

**Grounding control:** Qwen receives only reranked evidence and must cite it. Insufficient evidence produces an abstention rather than an answer from pretrained memory.

## Slide 3 — Lessons learned and business value

**Lessons learned**

- Better retrieval and reranking improve answers more reliably than prompt expansion.
- Streaming improves perceived responsiveness; persistence and error states make it a product.
- Golden data defines expected behavior, DeepEval grades it, and human feedback finds real failures.
- Repository-specific AI instructions make coding agents safer and more consistent.

**Business value**

- Faster access to security-control guidance with page-level auditability.
- Private local inference for sensitive internal documents.
- Saved investigations and response versions improve analyst continuity.
- Feedback tied to exact versions creates a measurable improvement loop: low rating → review evidence → add regression case → refine retrieval → reevaluate.

**Next:** multi-document ingestion, feedback analytics, production authentication, and monitoring.
