# Sentinel — Presentation Guide

## Slide 1 — Goal

Build a private RAG assistant that answers CIS Controls questions from the supplied document, cites the exact pages, measures retrieval quality, and abstains when the source lacks evidence.

## Slide 2 — End-to-end architecture

```text
CIS PDF → Unstructured hi_res → title-aware chunks → BGE-small → Weaviate
Question → BM25 + BGE retrieval → BGE/MiniLM rerank → Qwen3:4b → citations
                                               ↘ golden evaluation ↘ feedback
```

## Slide 3 — Parsing and cleaning

- Unstructured `hi_res` with Poppler and Tesseract preserves layout, titles, tables, images, source, category, and page metadata.
- Measured: 2,655 elements across 82 PDF pages and 225,616 characters.
- Extracted types: 636 narrative text, 318 titles, 147 list items, 50 tables, 16 images, 1 header, and 1,487 generic text elements.
- Cleaning removes empty content and normalizes repeated whitespace; it does not discard meaningful source text.

## Slide 4 — Chunking experiment

- Recursive character: 2,655 chunks, average 85 characters.
- Token-aware: 2,654 chunks, average 85 characters.
- Title-aware: 332 chunks, average 691 characters.
- Title-aware chunks were selected because they combine small layout elements into more coherent sections while retaining headings and page metadata.

## Slide 5 — Embeddings and vector storage

- Exact requested embedding: `BAAI/bge-small-en-v1.5` through `langchain-huggingface`.
- 332 selected chunks become 332 normalized vectors with 384 dimensions.
- Docker Weaviate persists the exact pipeline through `langchain-weaviate`.
- The live demo also keeps a 127-vector compact index for fast laptop startup.

## Slide 6 — Retrieval

- BM25 handles exact names, safeguard identifiers, and CIS terminology.
- BGE semantic similarity handles paraphrases and scenarios.
- Structural scoring favors authoritative control pages and down-ranks contents/index pages.

## Slide 7 — Reranking

- Exact model: `BAAI/bge-reranker-v2-m3`; verified locally on the Implementation Groups query.
- Practical live model: MiniLM cross-encoder, chosen for lower CPU/RAM and better response time.
- Both read the question and passage together rather than relying only on independent vectors.

## Slide 8 — Grounded generation

- Local `qwen3:4b` runs through Ollama with temperature 0.1.
- The prompt permits only retrieved context and requires numbered citations.
- If Ollama is offline, a deterministic cited extractive response remains available.
- Unsupported years and live-price questions return insufficient evidence with no misleading sources.

## Slide 9 — Golden dataset

- 20 labeled questions: direct facts, paraphrases, workplace scenarios, multiple controls, and two deliberate out-of-scope cases.
- Every case defines expected terms and source pages; abstention cases explicitly require no sources.
- Dataset: `evaluation/questions.json`; runner: `evaluation/evaluate.py`.

## Slide 10 — Measured results

| Metric | Result |
|---|---:|
| Evidence-term recall | 100% |
| Hit@5 | 100% |
| MRR@5 | 0.95 |
| Abstention accuracy | 100% |
| Automated tests | 9/9 passing |

These are project-set results, not a claim of universal accuracy.

## Slide 11 — Ablation study

| Pipeline | Hit@5 | MRR@5 | Average latency |
|---|---:|---:|---:|
| BM25 | 100% | 0.898 | 12 ms |
| BM25 + BGE | 100% | 0.907 | 301 ms |
| BM25 + BGE + MiniLM | 100% | 0.944 | 627 ms |

The experiment shows that semantic retrieval and reranking improve ordering while adding latency.

## Slide 12 — DeepEval

DeepEval 4.1.0 evaluated 20 human-labeled cases with local Qwen3:4b as the judge. The run produced 92 judgments with a 91.3% pass rate: Answer Relevancy 0.978, Faithfulness 0.725, Contextual Relevancy 0.715, Contextual Precision 0.993, Contextual Recall 0.956, and Safe Abstention 0.900. The lower contextual-relevancy score shows that some live chunks contain useful evidence plus neighboring noise. The report retains raw judge reasons, including several internally inconsistent faithfulness judgments, as a limitation of a small self-judge.

## Slide 13 — Live demo

1. Show the Knowledge Base status and Evaluation dashboard.
2. Ask “What is CIS Control 1, and why is it important?”
3. Ask a paraphrase about the laptop/device inventory review schedule.
4. Ask the former-employee account scenario.
5. Ask the deliberately unsupported Lebanon 2026 question and show safe abstention.
6. Open citations, submit feedback, and show the golden metrics.

## Short oral summary

“Sentinel parses the CIS PDF with layout-aware Unstructured, compares three chunking methods, embeds 332 selected chunks with BGE-small, and stores them in Weaviate. At query time it combines BM25 and semantic retrieval, reranks candidates, and gives the best evidence to local Qwen through Ollama. Every answer exposes page citations, unsupported questions abstain, and a 20-case golden dataset measures retrieval, ranking, and safety. The exact requested stack is preserved alongside a compact runtime optimized for the live laptop demo.”
