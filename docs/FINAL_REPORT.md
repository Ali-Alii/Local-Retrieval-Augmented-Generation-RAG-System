# Sentinel Final Project Report

## Executive summary

Sentinel is a fully local retrieval-augmented generation system that lets users explore CIS Controls v8 through traceable, source-grounded answers. The project began as a document RAG pipeline and was extended into a professional application with a React chat interface, a secure .NET middleware, a Python FastAPI RAG service, Weaviate retrieval, Ollama/Qwen generation, MongoDB persistence, streaming responses, citations, response versioning, and structured feedback. The result is a private cybersecurity knowledge workspace rather than a generic chatbot.

## Objectives

The technical objectives were to parse and index the supplied PDF, retrieve relevant passages, rerank them, generate answers constrained to the evidence, cite source pages, and evaluate retrieval and generation quality. The application objectives were to provide a responsive chat experience, preserve conversations, support regeneration, collect human feedback, document the system, and make it reproducible for another developer.

## What was delivered

- A local exact RAG pipeline over the CIS Controls v8 document.
- A React 19 and TypeScript interface with Markdown, SSE token streaming, loading states, auto-scroll, thread history, citations, metadata, regeneration, version selection, feedback, and a guided tour.
- A .NET 9 middleware that handles authentication, authorization, rate limiting, audit logging, API validation, Python proxying, SSE forwarding, and MongoDB persistence.
- A FastAPI service exposing versioned health, status, query, streaming, feedback, and evaluation endpoints.
- MongoDB collections for users, sessions, conversations, response versions, feedback, and audit events.
- A 20-case golden dataset, deterministic retrieval evaluation, ablation comparisons, and local DeepEval judging.
- Feature branches, meaningful commits, checked-in AI instructions, setup documentation, tests, and final presentation material.

## Technology stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Radix UI | Accessible interactive chat experience |
| Middleware | .NET 9, ASP.NET Core | Security boundary, validation, persistence, and proxying |
| RAG API | Python 3.12, FastAPI | Retrieval and generation orchestration with SSE |
| Parsing | Unstructured `hi_res`, OCR, table/image extraction | Structure-aware PDF ingestion |
| Chunking | Title-aware chunking with strategy comparison | Semantically coherent retrieval units |
| Embeddings | `BAAI/bge-small-en-v1.5` | Dense semantic representation |
| Vector store | Weaviate in Docker | Hybrid BM25 and vector retrieval |
| Reranking | `BAAI/bge-reranker-v2-m3` | Cross-encoder relevance refinement |
| Generation | Qwen3:4b served by Ollama | Private, grounded local generation |
| Persistence | MongoDB 8 in Docker | Flexible nested conversations and feedback |
| Evaluation | Golden dataset and DeepEval | Repeatable deterministic and judge-based quality checks |

## AI and RAG integration

The ingestion pipeline processed 82 PDF pages and extracted 2,655 elements. It preserved headings, narrative text, lists, tables, images, page numbers, element categories, and source identifiers while normalizing empty content and repeated whitespace. Title-aware chunking selected 332 chunks. BGE-small converted each chunk into a 384-dimensional vector stored in Weaviate.

At query time, Weaviate combines lexical BM25 matching with BGE vector similarity. A BGE cross-encoder reranks the candidates because retrieval similarity alone does not always place the best evidence first. The highest-quality passages, source names, page numbers, and snippets become a grounded prompt. Ollama runs Qwen locally and streams generated tokens. The prompt instructs Qwen to use only supplied evidence and cite it using `[1]`, `[2]`, and similar markers. If retrieval evidence is insufficient, the system returns a deterministic abstention instead of relying on the model's pretrained general knowledge.

## Architecture decision

The most important decision was placing .NET between React and Python. React never connects directly to the model, vector store, or database. The middleware validates authenticated ownership, proxies SSE safely, stores only completed answers, and exposes stable typed contracts. This separation keeps RAG experimentation in Python while centralizing application security and persistence in .NET. It also prevents partial streamed responses from becoming the canonical stored answer.

MongoDB was selected because a conversation is naturally a nested document containing messages, response versions, active-version state, citations, runtime metadata, and timestamps. A Docker volume preserves this information after refreshes, service restarts, and container recreation.

## Evaluation and results

The golden dataset contains 20 direct, paraphrased, scenario, and expected-abstention questions. Retrieval achieved 100% Hit@5 and 0.95 MRR@5. The exact-stack DeepEval run performed 92 judgments and achieved a 97.83% overall pass rate. Metric pass rates were 100% answer relevancy, 94.44% faithfulness, 100% contextual relevancy, 100% contextual precision, 94.44% contextual recall, and 100% safe abstention.

These numbers are strong project evidence, but they are not universal guarantees. The golden dataset is intentionally transparent and limited to the supplied domain. Deterministic metrics are retained alongside the local Qwen judge because an LLM judge can itself be inconsistent.

## AI development tooling

The project used an AI coding agent for repository inspection, implementation support, code review, documentation, test generation, debugging, and Git workflow assistance. `CLAUDE.md` provides the persistent customization artifact used by Claude-compatible and other coding agents. It defines the exact architecture, repository boundaries, security rules, commands, and definition of done.

The artifact improved consistency by telling agents not to hardcode RAG answers, not to expose internal services, not to alter golden references to inflate metrics, and always to preserve source metadata and abstention behavior. AI suggestions were validated through code review, compilation, automated tests, and end-to-end requests rather than accepted blindly.

## Challenges and resolutions

1. **Retrieval returned topically related but incorrect passages.** Title-aware chunks, hybrid retrieval, reranking, and evidence thresholds improved context quality.
2. **A small local model could generate unsupported details.** The prompt was tightened, contexts were reduced to higher-quality evidence, citations were required, and deterministic abstention was added.
3. **Exact local inference was slow.** SSE and paced rendering provided immediate progress while retaining the requested exact stack; a reversible compact runtime was kept only for constrained demonstrations.
4. **Browser refresh initially lost conversations.** MongoDB conversation documents and authenticated thread APIs made chat state durable.
5. **Feedback initially appeared unresponsive.** Persistent selected-button styling, confirmation text, a toast, and error handling made the state change explicit.
6. **Moving the repository left stale startup assumptions.** The final setup uses relative paths and the real FastAPI entrypoint.

## Lessons learned

- Retrieval quality usually matters more than asking the generator to compensate for weak evidence.
- Streaming improves perceived responsiveness but does not reduce model computation time.
- Evaluation requires both a stable dataset and a grader; neither replaces the other.
- Human feedback is useful only when it is tied to exact message and response-version identifiers.
- Persistence, authentication, observability, and error states turn an AI prototype into an application.
- AI coding tools are most useful when constrained by repository-specific instructions and verified by tests.

## Business value

Sentinel shortens the time required to find and interpret security-control guidance while keeping every answer auditable. Security teams can ask natural-language questions, open the supporting page, resume previous investigations, compare regenerated answers, and flag weak responses. The feedback data identifies recurring retrieval or generation failures and can be converted into new golden test cases, creating a measurable improvement loop. Because the system runs locally, organizations can use internal security documents without sending them to an external model provider.

## Limitations and next steps

The current knowledge base contains one document, inference latency is CPU-dependent, local MongoDB and Weaviate are unauthenticated for development, and the golden set is small. Production work should add HTTPS, managed secrets, database authentication, role-based administration, background indexing, feedback analytics, more documents, larger evaluation coverage, and observability dashboards.

## Conclusion

The final system satisfies the requested happy path: users can authenticate, send a question, receive a streamed cited answer, regenerate it, switch versions, provide persisted feedback, refresh the browser, and resume a saved conversation. It demonstrates the complete journey from RAG experimentation to a documented and testable full-stack AI product.
