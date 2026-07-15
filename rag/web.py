from __future__ import annotations

import argparse
import json
import mimetypes
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .engine import RAGEngine

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
ENGINE = None


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"[CIS RAG] {format % args}")

    def _json(self, value, status=200):
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/status":
            return self._json(ENGINE.stats())
        if path == "/api/evaluation":
            report_path = ROOT / "evaluation" / "latest_report.json"
            comparison_path = ROOT / "evaluation" / "comparison_report.json"
            deepeval_path = ROOT / "evaluation" / "deepeval_report.json"
            report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
            comparison = json.loads(comparison_path.read_text(encoding="utf-8")) if comparison_path.exists() else {}
            deepeval = json.loads(deepeval_path.read_text(encoding="utf-8")) if deepeval_path.exists() else {}
            return self._json({"evaluation": report, "comparison": comparison, "deepeval": deepeval, "feedback": ENGINE.stats()})
        target = STATIC / ("index.html" if path == "/" else path.lstrip("/"))
        if not target.resolve().is_relative_to(STATIC.resolve()) or not target.is_file():
            return self.send_error(404)
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(target)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            path = urlparse(self.path).path
            payload = self._body()
            if path == "/api/ask":
                question = str(payload.get("question", "")).strip()
                if not question or len(question) > 1000:
                    return self._json({"error": "Question must contain 1–1000 characters."}, 400)
                return self._json(ENGINE.answer(question))
            if path == "/api/ingest":
                return self._json(ENGINE.ingest(bool(payload.get("force"))))
            if path == "/api/feedback":
                ENGINE.feedback(payload)
                return self._json({"ok": True})
            return self._json({"error": "Not found"}, 404)
        except Exception as exc:
            return self._json({"error": str(exc)}, 500)


def run():
    global ENGINE
    parser = argparse.ArgumentParser(description="Run the private CIS Controls RAG workspace")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--runtime", choices=("exact", "compact"), default=os.getenv("RAG_RUNTIME", "exact"), help="exact uses Weaviate+BGE reranker; compact restores the fast JSON+MiniLM runtime")
    args = parser.parse_args()
    if args.runtime == "exact":
        from .exact_runtime import ExactRAGEngine

        ENGINE = ExactRAGEngine()
    else:
        ENGINE = RAGEngine()
    print(f"\n  CIS Controls Intelligence: http://{args.host}:{args.port} [{args.runtime}]\n")
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
