"""Ablation study: lexical vs hybrid vs hybrid + neural reranking."""
import json
import sys
import time
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.engine import ROOT, RAGEngine


def score(engine, cases, semantic, reranker):
    rows = []
    started = time.perf_counter()
    for case in cases:
        if case.get("expect_abstain"):
            continue
        before = time.perf_counter()
        results = engine.retrieve(case["question"], use_semantic=semantic, use_reranker=reranker)
        pages = [result["page"] for result in results]
        rank = next((index + 1 for index, page in enumerate(pages) if page in case["expected_pages"]), None)
        rows.append({"question": case["question"], "hit": rank is not None, "rr": 1 / rank if rank else 0, "latency_ms": round((time.perf_counter() - before) * 1000)})
    return {
        "hit_at_5": mean(row["hit"] for row in rows),
        "mrr_at_5": mean(row["rr"] for row in rows),
        "average_latency_ms": round(mean(row["latency_ms"] for row in rows)),
        "total_seconds": round(time.perf_counter() - started, 2),
        "results": rows,
    }


if __name__ == "__main__":
    engine = RAGEngine()
    cases = json.loads((ROOT / "evaluation" / "questions.json").read_text(encoding="utf-8"))
    report = {
        "dataset_size": len(cases),
        "lexical_bm25": score(engine, cases, False, False),
        "hybrid_bm25_bge": score(engine, cases, True, False),
        "hybrid_plus_minilm": score(engine, cases, True, True),
    }
    target = ROOT / "evaluation" / "comparison_report.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({name: {k: v for k, v in data.items() if k != "results"} if isinstance(data, dict) else data for name, data in report.items()}, indent=2))
