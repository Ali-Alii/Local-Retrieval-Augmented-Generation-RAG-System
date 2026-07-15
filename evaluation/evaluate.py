"""Small, transparent retrieval evaluation harness (Task 3.1)."""
import argparse
import json
import sys
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.engine import ROOT, RAGEngine


def evaluate(output: Path) -> dict:
    engine = RAGEngine()
    if not engine.chunks:
        engine.ingest()
    cases = json.loads((ROOT / "evaluation" / "questions.json").read_text(encoding="utf-8"))
    rows = []
    for case in cases:
        if case.get("expect_abstain"):
            answer = engine.answer(case["question"])
            abstained = answer["mode"] == "insufficient-evidence" and not answer["sources"]
            rows.append({**case, "abstained": abstained, "keyword_recall": 1.0 if abstained else 0.0, "page_hit": abstained, "reciprocal_rank": 1.0 if abstained else 0.0, "retrieved_pages": []})
            continue
        results = engine.retrieve(case["question"])
        combined = " ".join(item["text"].lower() for item in results)
        terms = [term.lower() for term in case["expected_terms"]]
        keyword_recall = sum(term in combined for term in terms) / len(terms)
        page_hit = any(item["page"] in case["expected_pages"] for item in results)
        reciprocal_rank = next((1 / (i + 1) for i, item in enumerate(results) if item["page"] in case["expected_pages"]), 0)
        rows.append({**case, "keyword_recall": keyword_recall, "page_hit": page_hit, "reciprocal_rank": reciprocal_rank, "retrieved_pages": [x["page"] for x in results]})
    report = {"cases": len(rows), "golden_dataset": True, "keyword_recall": mean(x["keyword_recall"] for x in rows), "hit_rate_at_5": mean(x["page_hit"] for x in rows), "mrr_at_5": mean(x["reciprocal_rank"] for x in rows), "abstention_accuracy": mean(x.get("abstained", True) for x in rows if x.get("expect_abstain")) if any(x.get("expect_abstain") for x in rows) else None, "results": rows}
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "evaluation" / "latest_report.json")
    report = evaluate(parser.parse_args().output)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
