# Sentinel — Local CIS Controls RAG

Sentinel is a private, source-grounded RAG workspace for the supplied CIS Controls v8 PDF. It completes internship tasks 2.1–2.7 and 3.1–3.2: structured parsing, chunk comparison, embeddings, vector storage, ingestion, reranking, grounded generation, evaluation, and human feedback.

## Quick start

Requirements: Python 3.12, `uv`, Docker Desktop, Poppler, Tesseract, and Ollama with `qwen3:4b` for fluent local generation.

```powershell
uv sync --python 3.12
docker compose up -d
uv run python main.py
```

Open `http://127.0.0.1:8000`. If Ollama is offline, answers switch safely to a cited extractive fallback.

## Assignment mapping

| Task | Exact requested implementation | Optimized live implementation |
|---|---|---|
| 2.1 Parsing | Unstructured `hi_res`, OCR, tables, images, page metadata | pypdf page parser |
| 2.2 Chunking | LangChain recursive, token, and Unstructured title-aware comparison | 380 words, 55-word overlap |
| 2.3 Embedding | `BAAI/bge-small-en-v1.5` via `langchain-huggingface` | Same BGE model through quantized FastEmbed |
| 2.4 Storage | Docker Weaviate via `langchain-weaviate` | Portable local JSON index |
| 2.5 Ingestion | 332 title-aware chunks stored with metadata | Source fingerprint and incremental rebuild |
| 2.6 Reranking | `BAAI/bge-reranker-v2-m3` adapter in `rag/exact_reranker.py` | MiniLM cross-encoder for lower CPU/RAM cost |
| 2.7 Generation | Grounded prompt and local Qwen3:4b through Ollama | Same, with deterministic offline fallback |
| 3.1 Evaluation | 20-case golden dataset, Hit@5, MRR@5, recall, abstention, ablation, and DeepEval | Results exposed in the Evaluation UI |
| 3.2 HITL | Thumbs up/down feedback in local JSONL | Same |

The two paths are deliberate: the exact pipeline proves the specified stack, while the optimized path makes a responsive live demonstration possible on a laptop.

## Measured ingestion result

The verified `hi_res` run extracted **2,655 elements** from **82 PDF pages**: 636 narrative text elements, 318 titles, 147 list items, 50 tables, 16 images, 1 header, and 1,487 generic text elements. Title-aware chunking selected **332 chunks**, stored as **332 vectors × 384 dimensions** in Weaviate. The compact live index contains **127 chunks × 384 dimensions**.

Cleaning normalizes repeated whitespace and empty content while retaining headings, tables, page numbers, source names, element categories, and stable identifiers. It does not remove meaningful security text.

## Reproduce each stage

```powershell
uv run python -m rag.exact_pipeline analyze
uv run python -m rag.exact_pipeline weaviate
uv run python evaluation/evaluate.py
uv run python evaluation/compare.py
uv run python evaluation/deepeval_run.py
uv run python -m unittest discover -v
```

The first `analyze` run is CPU-heavy because layout inference processes every page; its selected chunks are cached in `.rag_data/unstructured_chunks.json`.

## Data flow

```text
CIS PDF → Unstructured hi_res → chunk comparison → BGE-small embeddings → Weaviate
Question → BM25 + BGE retrieval → cross-encoder rerank → Qwen3:4b → cited answer
                                      ↘ golden-set metrics   ↘ local feedback
```

DeepEval uses local Qwen3:4b as an offline judge. Across 92 judgments it measured 0.978 answer relevancy, 0.725 faithfulness, 0.715 contextual relevancy, 0.993 contextual precision, 0.956 contextual recall, 0.900 safe abstention, and a 91.3% overall pass rate. See `evaluation/DEEPEVAL_REPORT.md` for interpretation and limitations.

Key files: `rag/exact_pipeline.py`, `rag/engine.py`, `rag/exact_reranker.py`, `evaluation/questions.json`, `evaluation/evaluate.py`, `evaluation/compare.py`, `evaluation/deepeval_run.py`, and `notebooks/01_RAG_setup.ipynb`.

## Safety and limitations

- The app binds to localhost and keeps documents, models, and feedback on the machine.
- Unsupported or time-sensitive questions abstain instead of forcing an answer from irrelevant passages.
- A 20-question golden set is transparent project evidence, not proof of universal accuracy.
- Always inspect cited pages for consequential security decisions.
