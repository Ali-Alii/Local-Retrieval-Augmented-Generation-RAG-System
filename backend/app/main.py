from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from rag.engine import RAGEngine
from .schemas import AskRequest, FeedbackRequest

ROOT = Path(__file__).resolve().parents[2]


def create_engine():
    if os.getenv("RAG_RUNTIME", "exact") == "exact":
        from rag.exact_runtime import ExactRAGEngine
        return ExactRAGEngine()
    return RAGEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.engine = await asyncio.to_thread(create_engine)
    yield
    client = getattr(app.state.engine, "client", None)
    if client is not None and hasattr(client, "close"):
        client.close()


app = FastAPI(title="Sentinel RAG API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok", "service": "sentinel-api"}


@app.get("/api/v1/status")
async def status(request: Request) -> dict:
    return await asyncio.to_thread(request.app.state.engine.stats)


@app.post("/api/v1/ask")
async def ask(payload: AskRequest, request: Request) -> dict:
    try:
        return await asyncio.to_thread(request.app.state.engine.answer, payload.question.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/feedback")
async def feedback(payload: FeedbackRequest, request: Request) -> dict:
    await asyncio.to_thread(request.app.state.engine.feedback, payload.model_dump())
    return {"ok": True}


@app.get("/api/v1/evaluation")
async def evaluation() -> dict:
    paths = {
        "retrieval": ROOT / "evaluation" / "latest_report.json",
        "comparison": ROOT / "evaluation" / "comparison_report.json",
        "deepeval": ROOT / "evaluation" / "deepeval_exact_report.json",
    }
    return {name: json.loads(path.read_text(encoding="utf-8")) if path.exists() else {} for name, path in paths.items()}
