# DeepEval Evaluation Report

## Final exact-stack evaluation

The final run evaluated the required exact pipeline (Unstructured `hi_res`, title-aware chunks, `BAAI/bge-small-en-v1.5`, Docker Weaviate, `BAAI/bge-reranker-v2-m3`, and Qwen3:4b through Ollama) on the unchanged 20-case golden dataset. It completed 92 judgments with a **97.83% overall pass rate**.

| DeepEval metric | Average | Pass rate |
|---|---:|---:|
| Answer Relevancy | 0.9722 | 100.00% |
| Faithfulness | 0.8620 | 94.44% |
| Contextual Relevancy | 0.8541 | 100.00% |
| Contextual Precision | 1.0000 | 100.00% |
| Contextual Recall | 0.9259 | 94.44% |
| Safe Abstention | 0.9000 | 100.00% |

The raw exact-stack cases and judge reasons are retained in `deepeval_exact_cases.json` and `deepeval_exact_report.json`. Pass rates and averages are both reported because they answer different questions: the average shows score strength, while the pass rate shows the proportion meeting DeepEval's fixed 0.5 threshold.

## Historical compact baseline

## Method

- Framework: DeepEval 4.1.0
- Dataset: 20 human-authored golden questions and reference answers
- Judge: local `qwen3:4b` through Ollama, temperature 0, thinking disabled
- Evaluated runtime: compact 127-chunk JSON/FastEmbed/MiniLM baseline
- Threshold: 0.5 for every metric
- Answerable cases: 18, each scored for Answer Relevancy, Faithfulness, Contextual Relevancy, Contextual Precision, and Contextual Recall
- Unsupported cases: 2, scored with a Safe Abstention GEval criterion
- Cloud services: none; answers, retrieved context, references, and judgments remain local

The actual Sentinel answers and retrieved passages were cached before judging. This prevents reference answers from leaking into generation and makes reruns reproducible.

## Results

| DeepEval metric | Average | Pass rate |
|---|---:|---:|
| Answer Relevancy | 0.978 | 100.0% |
| Faithfulness | 0.725 | 77.8% |
| Contextual Relevancy | 0.715 | 83.3% |
| Contextual Precision | 0.993 | 100.0% |
| Contextual Recall | 0.956 | 94.4% |
| Safe Abstention | 0.900 | 100.0% |

Overall, 84 of 92 metric judgments passed: **91.3%**.

## Interpretation

- Answer Relevancy shows that generated responses directly address the questions.
- Contextual Precision shows that the reranker generally orders useful evidence before less useful evidence.
- Contextual Recall confirms that retrieved evidence usually covers the human reference answer.
- Contextual Relevancy is lower because several 380-word chunks include the correct evidence plus unrelated neighboring material. Smaller or title-aware chunks in the live runtime are the clearest next experiment.
- Faithfulness identifies some generation-risk cases, but three zero scores include judge reasons saying there were no contradictions. This internal inconsistency is a limitation of using the same 4B local model as evaluator. The raw reasons are retained in `deepeval_report.json` and should be reported rather than hidden.
- Both unsupported questions passed safe abstention, confirming that Sentinel did not invent current or geographically specific facts absent from the CIS source.

## Reproduce

```powershell
ollama serve
uv run python evaluation/deepeval_run.py
```

Use `--refresh` only when new Sentinel outputs are required. Without it, the runner resumes missing or failed judgments from the cached cases and report.

## Evaluation artifacts

- `deepeval_goldens.json`: human references
- `deepeval_cases.json`: actual answers and retrieval context
- `deepeval_report.json`: raw scores, pass/fail status, reasons, and latency
- `deepeval_run.py`: offline, resumable evaluation runner
