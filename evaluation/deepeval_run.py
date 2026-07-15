"""Offline DeepEval RAG evaluation using local Qwen through Ollama.

The runner is deliberately resumable: generated RAG cases and every completed
metric are persisted so a long CPU-only evaluation can continue after interruption.
No Confident AI login or cloud upload is required.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from statistics import mean

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
    GEval,
)
from deepeval.models import OllamaModel
from deepeval.test_case import LLMTestCase, SingleTurnParams

from rag.engine import ROOT, RAGEngine

GOLDENS = ROOT / "evaluation" / "deepeval_goldens.json"
CASES = ROOT / "evaluation" / "deepeval_cases.json"
REPORT = ROOT / "evaluation" / "deepeval_report.json"
EVALUATED_RUNTIME = "compact"


class NoThinkingOllamaModel(OllamaModel):
    """DeepEval Ollama judge with Qwen's hidden reasoning disabled.

    DeepEval's stock adapter passes generation options but not Ollama's top-level
    `think` flag. Structured metric prompts do not benefit from a long hidden
    reasoning trace, so this keeps the same Qwen model while making a full local
    evaluation practical.
    """

    def generate(self, prompt: str, schema=None):
        client = self.load_model()
        response = client.chat(
            model=self.name,
            messages=[{"role": "user", "content": prompt}],
            format=schema.model_json_schema() if schema else "json",
            think=False,
            options={"temperature": 0, "num_ctx": 4096, "num_predict": 3000},
        )
        content = response.message.content
        return (schema.model_validate_json(content) if schema else content, 0)


def read_json(path: Path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_cases(engine: RAGEngine, goldens: list[dict], refresh: bool = False) -> list[dict]:
    cached = {} if refresh else {row["question"]: row for row in read_json(CASES, [])}
    output = []
    for index, golden in enumerate(goldens, 1):
        question = golden["question"]
        if question in cached:
            output.append(cached[question])
            continue
        print(f"[generate {index}/{len(goldens)}] {question}", flush=True)
        result = engine.answer(question)
        row = {
            **golden,
            "actual_output": result["answer"],
            # Evaluate the sentence-focused evidence actually supplied to Qwen,
            # not full storage chunks or extra UI-only citations.
            "retrieval_context": engine.generation_contexts(question, result["sources"]),
            "retrieved_pages": [source["page"] for source in result["sources"]],
            "answer_mode": result["mode"],
            "answer_latency_ms": result["latency_ms"],
        }
        output.append(row)
        write_json(CASES, output + [value for key, value in cached.items() if key not in {x["question"] for x in output}])
    write_json(CASES, output)
    return output


def metric_factories(judge):
    common = {"model": judge, "threshold": 0.5, "include_reason": True, "async_mode": False}
    return {
        "answer_relevancy": lambda: AnswerRelevancyMetric(**common),
        "faithfulness": lambda: FaithfulnessMetric(**common, truths_extraction_limit=5),
        "contextual_relevancy": lambda: ContextualRelevancyMetric(**common),
        "contextual_precision": lambda: ContextualPrecisionMetric(**common),
        "contextual_recall": lambda: ContextualRecallMetric(**common),
    }


def abstention_metric(judge):
    return GEval(
        name="Safe Abstention",
        criteria=("Determine whether the actual output correctly refuses to invent an answer that is absent or live "
                  "information, clearly states insufficient source evidence, and does not present unsupported facts."),
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
        model=judge,
        threshold=0.5,
        async_mode=False,
    )


def summarize(results: list[dict]) -> dict:
    scores: dict[str, list[float]] = {}
    passes = 0
    total = 0
    for row in results:
        for name, result in row.get("metrics", {}).items():
            if result.get("score") is None:
                continue
            scores.setdefault(name, []).append(float(result["score"]))
            passes += bool(result.get("passed"))
            total += 1
    return {
        "cases": len(results),
        "judge": "qwen3:4b via local Ollama",
        "evaluated_runtime": EVALUATED_RUNTIME,
        "threshold": 0.5,
        "metric_averages": {name: round(mean(values), 4) for name, values in scores.items()},
        "metric_pass_rates": {
            name: round(mean(row["metrics"][name]["passed"] for row in results if name in row.get("metrics", {})), 4)
            for name in scores
        },
        "overall_metric_pass_rate": round(passes / total, 4) if total else None,
        "completed_metric_runs": total,
    }


def run(limit: int | None, refresh: bool, runtime: str = "exact") -> dict:
    global CASES, REPORT, EVALUATED_RUNTIME
    EVALUATED_RUNTIME = runtime
    if runtime == "exact":
        CASES = ROOT / "evaluation" / "deepeval_exact_cases.json"
        REPORT = ROOT / "evaluation" / "deepeval_exact_report.json"
        from rag.exact_runtime import ExactRAGEngine
        engine = ExactRAGEngine()
    else:
        engine = RAGEngine()
    goldens = read_json(GOLDENS, [])[:limit]
    cases = prepare_cases(engine, goldens, refresh)
    previous = {} if refresh else {row["question"]: row for row in read_json(REPORT, {}).get("results", [])}
    judge = NoThinkingOllamaModel(model="qwen3:4b", base_url="http://127.0.0.1:11434", temperature=0, timeout=300)
    factories = metric_factories(judge)
    results = []
    for case_index, case in enumerate(cases, 1):
        row = previous.get(case["question"], {"question": case["question"], "metrics": {}})
        test_case = LLMTestCase(
            input=case["question"],
            actual_output=case["actual_output"],
            expected_output=case["reference_answer"],
            retrieval_context=case["retrieval_context"],
        )
        selected = {"safe_abstention": lambda: abstention_metric(judge)} if case.get("expect_abstain") else factories
        for name, factory in selected.items():
            if name in row["metrics"] and row["metrics"][name].get("score") is not None and not refresh:
                continue
            print(f"[judge {case_index}/{len(cases)}] {name}: {case['question']}", flush=True)
            started = time.perf_counter()
            try:
                metric = factory()
                metric.measure(test_case)
                value = {
                    "score": float(metric.score),
                    "passed": bool(metric.is_successful()),
                    "reason": metric.reason,
                    "threshold": float(metric.threshold),
                    "elapsed_seconds": round(time.perf_counter() - started, 2),
                }
            except Exception as exc:
                value = {"score": None, "passed": False, "error": f"{type(exc).__name__}: {exc}", "elapsed_seconds": round(time.perf_counter() - started, 2)}
            row["metrics"][name] = value
            current = results + [row]
            payload = {"summary": summarize(current), "results": current}
            write_json(REPORT, payload)
        results.append(row)
    report = {"summary": summarize(results), "results": results}
    write_json(REPORT, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, help="Evaluate only the first N goldens (useful for a smoke test).")
    parser.add_argument("--refresh", action="store_true", help="Regenerate answers and rerun completed metrics.")
    parser.add_argument("--runtime", choices=("exact", "compact"), default="exact",
                        help="Pipeline to generate and evaluate (default: exact assignment stack).")
    args = parser.parse_args()
    final = run(args.limit, args.refresh, args.runtime)
    print(json.dumps(final["summary"], indent=2))
