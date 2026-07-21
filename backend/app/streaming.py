from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator

from ollama import Client


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class FinalAnswerFilter:
    """Keep Qwen reasoning private and release only final-answer token chunks."""

    def __init__(self):
        self.pending = ""
        self.visible = False

    def feed(self, content: str) -> list[str]:
        if self.visible:
            return [content]
        self.pending += content
        if "</think>" not in self.pending:
            return []
        _reasoning, final = self.pending.split("</think>", 1)
        self.pending = ""
        self.visible = True
        return [final.lstrip()] if final.lstrip() else []

    def finish(self) -> list[str]:
        # Models that honor think=False may return the final answer without tags.
        if not self.visible and self.pending:
            final, self.pending = self.pending, ""
            return [final]
        return []


def unsupported(engine, question: str) -> bool:
    checker = getattr(engine, "_unsupported_exact", None) or getattr(engine, "_unsupported_question", None)
    return bool(checker and checker(question))


async def stream_rag_answer(engine, question: str) -> AsyncIterator[str]:
    """Retrieve evidence, then stream real final-answer Qwen tokens as SSE."""
    started = time.perf_counter()
    yield sse("status", {"phase": "retrieving", "message": "Searching and reranking CIS evidence…"})
    if unsupported(engine, question):
        refusal = "The indexed CIS Controls document does not contain enough evidence to answer that question. I won't infer or invent information beyond the provided source."
        yield sse("token", {"content": refusal})
        yield sse("done", {"mode": "insufficient-evidence", "runtime": "exact", "latency_ms": round((time.perf_counter() - started) * 1000)})
        return
    try:
        sources = await asyncio.to_thread(engine.retrieve, question)
        if not sources:
            raise RuntimeError("No relevant evidence was found in the indexed document.")
        excerpts = engine.generation_contexts(question, sources)
        context = "\n\n".join(f"[Source {index}, page {source['page']}] {excerpt}" for index, (source, excerpt) in enumerate(zip(sources[:3], excerpts), 1))
        prompt = (
            "Answer only from the supplied CIS Controls context. Every factual statement must be directly supported by the context. "
            "Do not add outside knowledge. Be concise and cite evidence with [1], [2], or [3]. A decimal identifier X.Y is Safeguard "
            "X.Y under Control X. Markdown bold text, lists, and code blocks are allowed when useful. If evidence is insufficient, say so."
            f"\n\nContext:\n{context}\n\nQuestion: {question}\n/no_think"
        )
        yield sse("status", {"phase": "generating", "message": "Qwen is composing a grounded answer…"})
        queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def generate() -> None:
            answer_filter = FinalAnswerFilter()
            try:
                stream = Client(host="http://127.0.0.1:11434", timeout=300).chat(
                    model="qwen3:4b", messages=[{"role": "user", "content": prompt}], stream=True, think=False,
                    options={"temperature": 0.1, "num_predict": 700, "num_ctx": 4096},
                )
                for part in stream:
                    if part.message.content:
                        for token in answer_filter.feed(part.message.content):
                            loop.call_soon_threadsafe(queue.put_nowait, ("token", token))
                for token in answer_filter.finish():
                    loop.call_soon_threadsafe(queue.put_nowait, ("token", token))
            except Exception as exc:
                loop.call_soon_threadsafe(queue.put_nowait, ("error", str(exc)))
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, ("complete", None))

        worker = asyncio.create_task(asyncio.to_thread(generate))
        while True:
            event, value = await queue.get()
            if event == "complete": break
            if event == "error": raise RuntimeError(value or "Local model generation failed.")
            yield sse("token", {"content": value})
        await worker
        yield sse("done", {"mode": "ollama-stream", "runtime": "exact" if engine.__class__.__name__.startswith("Exact") else "compact", "latency_ms": round((time.perf_counter() - started) * 1000)})
    except Exception as exc:
        yield sse("error", {"message": str(exc)})
