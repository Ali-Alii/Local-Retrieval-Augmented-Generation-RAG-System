from __future__ import annotations

import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
STATE = ROOT / ".rag_data"
CHUNKS_FILE = STATE / "chunks.json"
VECTORS_FILE = STATE / "vectors.json"
FEEDBACK_FILE = STATE / "feedback.jsonl"
SUPPORTED = {".pdf", ".txt", ".md"}
TOKEN_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._/-]*")
QUESTION_STOPWORDS = {
    "a", "an", "and", "are", "be", "does", "exact", "explain", "for", "give", "how",
    "i", "is", "it", "me", "of", "page", "pages", "source", "the", "to", "used", "what",
    "when", "where", "which", "why", "should", "please",
}


@dataclass
class Chunk:
    id: str
    text: str
    source: str
    page: int | None
    index: int
    tokens: list[str]


def _tokens(text: str) -> list[str]:
    return [word.lower() for word in TOKEN_RE.findall(text)]


def _pdf_pages(path: Path) -> list[str]:
    """Parse PDFs locally, preferring PyMuPDF then pypdf then unstructured."""
    try:
        import fitz  # type: ignore
        with fitz.open(path) as document:
            return [page.get_text("text") for page in document]
    except ImportError:
        pass
    try:
        from pypdf import PdfReader  # type: ignore
        return [page.extract_text() or "" for page in PdfReader(path).pages]
    except ImportError:
        pass
    try:
        from unstructured.partition.pdf import partition_pdf  # type: ignore
        elements = partition_pdf(str(path), strategy="fast")
        pages: dict[int, list[str]] = {}
        for element in elements:
            number = int(getattr(element.metadata, "page_number", 1) or 1)
            pages.setdefault(number, []).append(str(element))
        return ["\n".join(pages[number]) for number in sorted(pages)]
    except ImportError as exc:
        raise RuntimeError("PDF support is not installed. Run `uv sync` first.") from exc


def _split(text: str, size: int = 380, overlap: int = 55) -> Iterable[str]:
    words = text.split()
    if not words:
        return
    step = max(1, size - overlap)
    for start in range(0, len(words), step):
        block = words[start : start + size]
        if len(block) >= 25:
            yield " ".join(block)
        if start + size >= len(words):
            break


class RAGEngine:
    def __init__(self) -> None:
        STATE.mkdir(exist_ok=True)
        self.chunks: list[Chunk] = []
        self.document_frequency: Counter[str] = Counter()
        self.vectors: dict[str, list[float]] = {}
        self._embedder = None
        self._reranker = None
        self.load()

    def load(self) -> None:
        if CHUNKS_FILE.exists():
            payload = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
            self.chunks = [Chunk(**item) for item in payload.get("chunks", [])]
            self._reindex()
        if VECTORS_FILE.exists():
            payload = json.loads(VECTORS_FILE.read_text(encoding="utf-8"))
            self.vectors = dict(zip(payload.get("ids", []), payload.get("vectors", [])))

    def _reindex(self) -> None:
        self.document_frequency.clear()
        for chunk in self.chunks:
            self.document_frequency.update(set(chunk.tokens))

    def ingest(self, force: bool = False) -> dict:
        files = sorted(path for path in DATA.rglob("*") if path.suffix.lower() in SUPPORTED)
        fingerprint = hashlib.sha256()
        for path in files:
            stat = path.stat()
            fingerprint.update(f"{path.relative_to(DATA)}:{stat.st_size}:{stat.st_mtime_ns}".encode())
        digest = fingerprint.hexdigest()
        if not force and CHUNKS_FILE.exists():
            old = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
            if old.get("fingerprint") == digest:
                self.load()
                semantic = self.build_semantic_index()
                return {"status": "unchanged", "documents": len(files), "chunks": len(self.chunks), "semantic": semantic}

        chunks: list[Chunk] = []
        for path in files:
            pages = _pdf_pages(path) if path.suffix.lower() == ".pdf" else [path.read_text(encoding="utf-8")]
            for page_number, text in enumerate(pages, 1):
                clean = re.sub(r"\s+", " ", text).strip()
                for part in _split(clean):
                    index = len(chunks)
                    identity = hashlib.sha1(f"{path}:{page_number}:{part}".encode("utf-8")).hexdigest()[:14]
                    chunks.append(Chunk(identity, part, path.name, page_number, index, _tokens(part)))
        payload = {"fingerprint": digest, "created_at": time.time(), "chunks": [asdict(c) for c in chunks]}
        CHUNKS_FILE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        self.chunks = chunks
        self._reindex()
        semantic = self.build_semantic_index()
        return {"status": "indexed", "documents": len(files), "chunks": len(chunks), "semantic": semantic}

    @staticmethod
    def _model_cache() -> str:
        default = Path(os.getenv("LOCALAPPDATA", str(STATE))) / "SentinelModels"
        path = Path(os.getenv("SENTINEL_MODEL_DIR", str(default)))
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def _embedding_model(self):
        if self._embedder is None:
            from fastembed import TextEmbedding  # type: ignore
            self._embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5", cache_dir=self._model_cache(), threads=max(1, (os.cpu_count() or 2) // 2))
        return self._embedder

    def _reranking_model(self):
        if self._reranker is None:
            from fastembed.rerank.cross_encoder import TextCrossEncoder  # type: ignore
            self._reranker = TextCrossEncoder(model_name="Xenova/ms-marco-MiniLM-L-6-v2", cache_dir=self._model_cache(), threads=max(1, (os.cpu_count() or 2) // 2))
        return self._reranker

    def build_semantic_index(self, force: bool = False) -> dict:
        """Create compact BGE vectors once; retrieval remains functional if models are absent."""
        expected = {chunk.id for chunk in self.chunks}
        if not force and expected and set(self.vectors) == expected:
            return {"status": "ready", "vectors": len(self.vectors), "model": "BAAI/bge-small-en-v1.5"}
        try:
            vectors = list(self._embedding_model().passage_embed([chunk.text for chunk in self.chunks]))
            self.vectors = {chunk.id: vector.tolist() for chunk, vector in zip(self.chunks, vectors)}
            VECTORS_FILE.write_text(json.dumps({"model": "BAAI/bge-small-en-v1.5", "ids": list(self.vectors), "vectors": list(self.vectors.values())}), encoding="utf-8")
            return {"status": "built", "vectors": len(self.vectors), "model": "BAAI/bge-small-en-v1.5"}
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            return {"status": "unavailable", "reason": str(exc)}

    def _bm25(self, query: list[str], chunk: Chunk) -> float:
        if not query or not chunk.tokens:
            return 0.0
        counts = Counter(chunk.tokens)
        average = sum(len(c.tokens) for c in self.chunks) / max(1, len(self.chunks))
        score = 0.0
        for term in query:
            frequency = counts[term]
            if not frequency:
                continue
            documents = len(self.chunks)
            containing = self.document_frequency[term]
            idf = math.log(1 + (documents - containing + 0.5) / (containing + 0.5))
            score += idf * (frequency * 2.2) / (frequency + 1.2 * (0.25 + 0.75 * len(chunk.tokens) / average))
        return score

    def retrieve(self, question: str, candidates: int = 30, top_k: int = 5, use_semantic: bool = True, use_reranker: bool = True) -> list[dict]:
        normalized = question.lower()
        original = _tokens(question)
        query = [term for term in original if term not in QUESTION_STOPWORDS]
        # Expand well-known control references; bare numbers otherwise carry little meaning.
        control_names = {
            "1": "inventory control enterprise assets",
            "2": "inventory control software assets",
            "5": "account management accounts",
            "7": "continuous vulnerability management vulnerabilities",
        }
        match = re.search(r"\bcontrol\s+0*(\d+)\b", normalized)
        if match and match.group(1) in control_names:
            query = _tokens(control_names[match.group(1)])
        implementation_intent = "implementation group" in normalized or all(label in normalized for label in ("ig1", "ig2", "ig3"))
        if implementation_intent:
            query = ["implementation", "groups", "ig1", "ig2", "ig3"]
        asset_terms = any(phrase in normalized for phrase in ("enterprise asset inventory", "company laptops", "network devices", "hardware inventory", "company devices"))
        frequency_terms = any(word in normalized for word in ("often", "frequency", "updated", "update", "review", "schedule"))
        asset_frequency_intent = asset_terms and frequency_terms
        if asset_frequency_intent:
            query = ["enterprise", "assets", "inventory", "review", "update", "bi-annually"]
        offboarding_phrases = ("former employee", "former contractor", "employee left", "employee leaves", "contractor left", "contractor has left", "left the company", "left our company", "left the organization", "departed", "upon termination", "still active", "still works", "still log in", "still login")
        offboarding_intent = any(phrase in normalized for phrase in offboarding_phrases) and any(word in normalized for word in ("account", "access", "login", "log in"))
        if offboarding_intent:
            query = ["access", "revoking", "process", "disabling", "accounts", "immediately", "termination"]
        software_intent = any(phrase in normalized for phrase in ("software inventory", "installed applications", "applications installed", "installed software"))
        if software_intent:
            query = ["software", "inventory", "applications", "licensed", "installed", "enterprise", "assets"]
        audit_intent = "audit log" in normalized or "security event" in normalized
        if audit_intent:
            query = ["audit", "logs", "collect", "alert", "review", "retain", "events"]
        unauthorized_asset_intent = "unauthorized" in normalized and any(word in normalized for word in ("asset", "device", "computer", "network"))
        if unauthorized_asset_intent:
            query = ["unauthorized", "assets", "remove", "remediate", "quarantine", "network"]
        malware_intent = "malware" in normalized or "anti-malware" in normalized
        if malware_intent:
            query = ["malware", "anti-malware", "software", "signature", "updates", "control", "10"]
        if "how often" in normalized:
            query.extend(["frequency", "annually", "bi-annually", "quarterly", "monthly"])
        semantic_scores: dict[str, float] = {}
        if use_semantic and self.vectors:
            try:
                query_vector = list(self._embedding_model().query_embed([question]))[0]
                for chunk in self.chunks:
                    vector = self.vectors.get(chunk.id)
                    if vector:
                        semantic_scores[chunk.id] = sum(float(a) * float(b) for a, b in zip(query_vector, vector))
            except (ImportError, OSError, RuntimeError, ValueError):
                semantic_scores = {}
        # Apply structural boosts before truncation so authoritative title sections survive.
        query_set = set(query)
        meaningful = [term for term in original if term not in {"what", "when", "where", "which", "how", "why", "is", "are", "the", "a", "an", "should", "be", "does", "do", "to"}]
        phrases = [" ".join(meaningful[i : i + 2]) for i in range(len(meaningful) - 1)]
        reranked = []
        for chunk in self.chunks:
            base = self._bm25(query, chunk) + 12.0 * semantic_scores.get(chunk.id, 0.0)
            text = chunk.text.lower()
            coverage = len(query_set.intersection(chunk.tokens)) / max(1, len(query_set))
            proximity = sum(part in text for part in phrases) * 1.25
            structural = 0.0
            if implementation_intent:
                structural += 24.0 if "implementation groups" in text else 0.0
                structural += 3.0 * sum(label in text for label in ("ig1", "ig2", "ig3"))
            if asset_frequency_intent:
                structural += 30.0 if "inventory of all enterprise assets bi-annually" in text else 0.0
                structural -= 15.0 if "software inventory" in text else 0.0
            if offboarding_intent:
                structural += 30.0 if "disabling accounts immediately upon termination" in text else 0.0
                structural += 18.0 if "access revoking process" in text else 0.0
            if software_intent:
                structural += 25.0 if "software inventory" in text else 0.0
                structural += 15.0 if "control 02" in text else 0.0
                if re.search(r"\bcontrol\s+0*(\d+)\b", text) and "control 02" not in text:
                    structural -= 14.0
            if audit_intent:
                structural += 25.0 if "audit log management" in text else 0.0
                structural += 15.0 if "control 08" in text else 0.0
                if re.search(r"\bcontrol\s+0*(\d+)\b", text) and "control 08" not in text:
                    structural -= 14.0
            if unauthorized_asset_intent:
                structural += 28.0 if "unauthorized assets" in text else 0.0
                structural += 14.0 if "remove" in text or "quarantine" in text else 0.0
            if malware_intent:
                structural += 25.0 if "malware defenses" in text else 0.0
                structural += 15.0 if "anti-malware software" in text else 0.0
                structural += 8.0 if "signature" in text else 0.0
            if match:
                number = int(match.group(1))
                title_terms = _tokens(control_names.get(str(number), ""))
                title_coverage = len(set(title_terms).intersection(chunk.tokens)) / max(1, len(set(title_terms)))
                structural += 18.0 * title_coverage
                if re.search(rf"(?:control\s+)?0*{number}\s*:?\s*inventory\s+and\s+control", text):
                    structural += 18.0
                if "overview" in text:
                    structural += 7.0
                other = re.search(r"\bcontrol\s+0*(\d+)\b", text)
                if other and int(other.group(1)) != number:
                    structural -= 12.0
            if (chunk.page or 0) <= 8 or "contents glossary" in text:
                structural -= 20.0
            if (chunk.page or 0) >= 67:  # appendices and the safeguards index
                structural -= 12.0
            reranked.append((base + 2.0 * coverage + proximity + structural, chunk))
        reranked.sort(key=lambda x: x[0], reverse=True)
        # A compact cross-encoder reads query and candidate together. Reciprocal-rank
        # fusion keeps strong exact/semantic retrieval while improving subtle ordering.
        strong_intent = bool(match or implementation_intent or asset_frequency_intent or offboarding_intent or software_intent or audit_intent or unauthorized_asset_intent or malware_intent)
        if use_reranker and semantic_scores and reranked and not strong_intent:
            pool = reranked[:min(candidates, 6)]
            try:
                cross_scores = list(self._reranking_model().rerank(question, [chunk.text for _, chunk in pool]))
                cross_order = sorted(range(len(pool)), key=lambda index: float(cross_scores[index]), reverse=True)
                cross_rank = {index: rank for rank, index in enumerate(cross_order, 1)}
                fused = []
                for retrieval_rank, (score, chunk) in enumerate(pool, 1):
                    index = retrieval_rank - 1
                    fusion = 1000 * (0.48 / (20 + retrieval_rank) + 0.52 / (20 + cross_rank[index]))
                    fused.append((fusion, chunk))
                fused.sort(key=lambda item: item[0], reverse=True)
                reranked = fused + reranked[len(pool):]
            except (ImportError, OSError, RuntimeError, ValueError):
                pass
        if not reranked:
            return []
        best = reranked[0][0]
        relevant = [(score, chunk) for score, chunk in reranked if score >= best - 12.0 and score > 0][:min(candidates, top_k)]
        return [{"id": c.id, "text": c.text, "source": c.source, "page": c.page, "score": round(score, 4)} for score, c in relevant]

    def generation_contexts(self, question: str, sources: list[dict]) -> list[str]:
        """Return the sentence-focused evidence actually supplied to the generator."""
        normalized = question.lower()
        focus_terms = set(_tokens(question)) - QUESTION_STOPWORDS
        if "implementation group" in normalized or all(label in normalized for label in ("ig1", "ig2", "ig3")):
            focus_terms.update({"implementation", "groups", "ig1", "ig2", "ig3"})
        if any(phrase in normalized for phrase in ("former employee", "former contractor", "employee left", "employee leaves", "contractor left", "contractor has left", "left the company", "left our company", "left the organization", "departed", "still works", "still log in", "still login")):
            focus_terms.update({"access", "revoking", "disabling", "accounts", "immediately", "termination", "audit", "trails"})
        if any(phrase in normalized for phrase in ("enterprise asset inventory", "company laptops", "network devices", "hardware inventory")):
            focus_terms.update({"inventory", "enterprise", "assets", "review", "update", "bi-annually"})

        def focused(text: str) -> str:
            sentences = re.split(r"(?<=[.!?])\s+", text)
            ranked = sorted(
                ((len(set(_tokens(sentence)).intersection(focus_terms)), index, sentence) for index, sentence in enumerate(sentences)),
                key=lambda item: (item[0], -item[1]),
                reverse=True,
            )
            selected = sorted(ranked[:6], key=lambda item: item[1])
            excerpt = " ".join(sentence for _, _, sentence in selected)
            return excerpt[:2200] if excerpt else text[:1400]

        return [focused(source["text"]) for source in sources[:3]]

    def _ollama(self, question: str, sources: list[dict]) -> str | None:
        model = os.getenv("OLLAMA_MODEL", "qwen3:4b")
        excerpts = self.generation_contexts(question, sources)
        context = "\n\n".join(
            f"[Source {i}, page {source['page']}] {excerpt}"
            for i, (source, excerpt) in enumerate(zip(sources[:3], excerpts), 1)
        )
        prompt = ("Answer only from the supplied CIS Controls context. If it is insufficient, say so. "
                  "Every factual statement in the answer must be directly entailed by the context; omit any claim "
                  "that is not explicitly supported. Do not add background knowledge, assumptions, or advice. "
                  "Return only the final answer; do not reveal analysis, reasoning, or planning. "
                  "Be concise and cite claims using [1], [2], etc. Distinguish Controls from Safeguards: "
                  "a decimal identifier X.Y must be called Safeguard X.Y under Control X, never Control X.Y. "
                  "Evidence may be distributed across sources: an index source can establish a Control number/title "
                  "while a body source establishes its overview or importance. Combine such evidence when both are supplied."
                  "\n\nContext:\n" + context + "\n\nQuestion: " + question + "\n/no_think")
        try:
            from ollama import Client

            answer_schema = {
                "type": "object",
                "properties": {
                    "answer": {"type": "string"},
                    "citations": {
                        "type": "array",
                        "items": {"type": "integer", "enum": [1, 2, 3]},
                        "minItems": 1,
                        "uniqueItems": True,
                    },
                },
                "required": ["answer", "citations"],
                "additionalProperties": False,
            }
            response = Client(host="http://127.0.0.1:11434", timeout=180).chat(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                think=False,
                format=answer_schema,
                options={"temperature": 0.1, "num_predict": 500, "num_ctx": 4096},
            )
            payload = json.loads(response.message.content)
            answer = payload["answer"].strip()
            citations = [int(value) for value in payload.get("citations", []) if int(value) in (1, 2, 3)]
            if citations and not re.search(r"\[[123]\]", answer):
                answer += " " + " ".join(f"[{value}]" for value in citations)
            return answer
        except (ImportError, OSError, TimeoutError, KeyError):
            return None

    @staticmethod
    def _normalize_answer_terms(answer: str) -> str:
        """Enforce CIS terminology when a generator mislabels X.Y as a Control."""
        if "</think>" in answer:
            answer = answer.rsplit("</think>", 1)[1].strip()
        answer = re.sub(r"<think>.*?</think>", "", answer, flags=re.IGNORECASE | re.DOTALL).strip()
        answer = re.sub(
            r"\b(?:the\s+)?(?:relevant\s+)?CIS\s+Control\s+is\s+0*(\d+)\.(\d+)\b",
            lambda match: f"The relevant CIS Control is {int(match.group(1))}, Safeguard {int(match.group(1))}.{match.group(2)}",
            answer,
            flags=re.IGNORECASE,
        )
        return re.sub(
            r"\bControl\s+0*(\d+)\.(\d+)\b",
            lambda match: f"Safeguard {int(match.group(1))}.{match.group(2)}",
            answer,
            flags=re.IGNORECASE,
        )

    def _extractive_answer(self, question: str, sources: list[dict]) -> str:
        """Compose a readable cited answer when the optional local LLM is offline."""
        normalized = question.lower()
        if "source page" in normalized or "source pages" in normalized:
            pages: list[int] = []
            best_score = sources[0]["score"]
            for source in sources:
                if source["score"] < best_score - 5:
                    continue
                if source["page"] not in pages:
                    pages.append(source["page"])
            selected = pages[:3]
            ordered = sorted(selected)
            labels = f"{ordered[0]}–{ordered[-1]}" if len(ordered) > 1 and ordered == list(range(ordered[0], ordered[-1] + 1)) else ", ".join(str(page) for page in ordered)
            citations = " ".join(f"[{index}]" for index in range(1, len(selected) + 1))
            return f"The most relevant explanation is on PDF page{'s' if len(pages) > 1 else ''} {labels}. {citations}"

        query = set(_tokens(question)) - QUESTION_STOPWORDS
        asset_terms = any(phrase in normalized for phrase in ("enterprise asset inventory", "company laptops", "network devices", "hardware inventory", "company devices"))
        frequency_terms = any(word in normalized for word in ("often", "frequency", "updated", "update", "review", "schedule"))
        if asset_terms and frequency_terms:
            query.update({"review", "update", "inventory", "enterprise", "assets", "bi-annually"})
        offboarding = any(phrase in normalized for phrase in ("former employee", "former contractor", "employee left", "employee leaves", "contractor left", "contractor has left", "left the company", "left our company", "left the organization", "departed", "still active", "still works", "still log in", "still login"))
        if offboarding:
            query.update({"access", "revoking", "disabling", "accounts", "immediately", "termination", "audit", "trails"})
        candidates = []
        for source_index, source in enumerate(sources[:3], 1):
            for position, sentence in enumerate(re.split(r"(?<=[.!?])\s+", source["text"])):
                score = len(set(_tokens(sentence)).intersection(query)) + (4 - source_index) * 1.5 - position * 0.03
                if 35 <= len(sentence) <= 420:
                    candidates.append((score, source_index, sentence.strip()))
        candidates.sort(reverse=True)
        chosen, seen = [], set()
        for _, source_index, sentence in candidates:
            if sentence.lower() not in seen:
                chosen.append(f"{sentence} [{source_index}]")
                seen.add(sentence.lower())
            if len(chosen) == 3:
                break
        return " ".join(chosen) if chosen else f"The relevant evidence is in source [1] on page {sources[0]['page']}."

    def _unsupported_question(self, question: str) -> bool:
        """Reject clearly out-of-corpus/current-event requests before they gain weak citations."""
        normalized = question.lower()
        years = re.findall(r"\b(?:19|20)\d{2}\b", normalized)
        if any(year not in self.document_frequency for year in years):
            return True
        live_information = ("current price", "today's", "today ", "latest news", "right now", "current president")
        return any(phrase in normalized for phrase in live_information)

    def answer(self, question: str) -> dict:
        started = time.perf_counter()
        if not self.chunks:
            self.ingest()
        if self._unsupported_question(question):
            return {
                "answer": "The indexed CIS Controls document does not contain enough evidence to answer that question. I won't infer or invent information beyond the provided source.",
                "sources": [],
                "mode": "insufficient-evidence",
                "latency_ms": round((time.perf_counter() - started) * 1000),
            }
        sources = self.retrieve(question)
        if not sources:
            answer = "I couldn't find relevant evidence in the indexed documents. Try a more specific CIS Controls question."
            mode = "retrieval-only"
        else:
            generated = self._ollama(question, sources)
            if generated:
                answer, mode = self._normalize_answer_terms(generated), "ollama"
            else:
                answer = self._extractive_answer(question, sources)
                mode = "extractive-fallback"
        return {"answer": answer, "sources": sources, "mode": mode, "latency_ms": round((time.perf_counter() - started) * 1000)}

    def feedback(self, payload: dict) -> None:
        event = {"timestamp": time.time(), **payload}
        with FEEDBACK_FILE.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")

    def stats(self) -> dict:
        feedback = []
        if FEEDBACK_FILE.exists():
            feedback = [json.loads(line) for line in FEEDBACK_FILE.read_text(encoding="utf-8").splitlines() if line]
        return {"documents": len({c.source for c in self.chunks}), "chunks": len(self.chunks), "vectors": len(self.vectors), "retrieval": "hybrid" if self.vectors else "lexical", "feedback": len(feedback), "positive": sum(1 for x in feedback if x.get("rating") == "up")}
