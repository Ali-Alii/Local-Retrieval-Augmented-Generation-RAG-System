"""Assignment-faithful LangChain + Unstructured + BGE + Weaviate pipeline.

This module coexists with Sentinel's compact runtime. It provides the exact teaching
stack requested in the supplied README and produces auditable stage statistics.
"""
from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from statistics import mean

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .engine import DATA, ROOT, STATE

PDF = DATA / "CIS_Controls__v8__Critical_Security_Controls__2023_08.pdf"
REPORT = ROOT / "evaluation" / "ingestion_report.json"
COLLECTION = "CISControlsV8"


def parse_hi_res(pdf: Path = PDF):
    """Task 2.1: layout-aware local parsing with titles, tables and images."""
    from unstructured.partition.pdf import partition_pdf

    return partition_pdf(
        filename=str(pdf),
        strategy="hi_res",
        infer_table_structure=True,
        extract_image_block_types=["Image", "Table"],
        extract_image_block_to_payload=False,
    )


def element_report(elements) -> dict:
    categories = Counter(type(element).__name__ for element in elements)
    pages = {getattr(element.metadata, "page_number", None) for element in elements}
    pages.discard(None)
    lengths = [len(str(element)) for element in elements if str(element).strip()]
    return {
        "elements": len(elements),
        "categories": dict(sorted(categories.items())),
        "pages": len(pages),
        "characters": sum(lengths),
        "average_element_characters": round(mean(lengths), 1) if lengths else 0,
    }


def elements_to_documents(elements) -> list[Document]:
    documents = []
    for index, element in enumerate(elements):
        text = " ".join(str(element).split())
        if not text:
            continue
        metadata = {
            "source": PDF.name,
            "page": getattr(element.metadata, "page_number", None),
            "category": type(element).__name__,
            "element_id": getattr(element, "id", str(index)),
        }
        documents.append(Document(page_content=text, metadata=metadata))
    return documents


def chunk_comparison(elements) -> dict[str, list[Document]]:
    """Task 2.2: compare recursive, token-aware and layout-aware by-title chunking."""
    documents = elements_to_documents(elements)
    recursive = RecursiveCharacterTextSplitter(
        chunk_size=1800,
        chunk_overlap=250,
        separators=["\n\n", "\n", ". ", " ", ""],
    ).split_documents(documents)
    token = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name="cl100k_base", chunk_size=400, chunk_overlap=60
    ).split_documents(documents)

    from unstructured.chunking.title import chunk_by_title

    title_elements = chunk_by_title(
        elements,
        max_characters=2000,
        new_after_n_chars=1600,
        combine_text_under_n_chars=350,
        overlap=200,
    )
    by_title = elements_to_documents(title_elements)
    return {"recursive": recursive, "token": token, "by_title": by_title}


def chunk_report(chunks: dict[str, list[Document]]) -> dict:
    output = {}
    for method, documents in chunks.items():
        lengths = [len(document.page_content) for document in documents]
        output[method] = {
            "chunks": len(documents),
            "average_characters": round(mean(lengths), 1) if lengths else 0,
            "minimum_characters": min(lengths, default=0),
            "maximum_characters": max(lengths, default=0),
        }
    return output


def langchain_embeddings():
    """Task 2.3: the exact LangChain Hugging Face wrapper requested by the README."""
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def connect_weaviate():
    import weaviate

    return weaviate.connect_to_local(host="127.0.0.1", port=8080, grpc_port=50051)


def store_in_weaviate(documents: list[Document]):
    """Task 2.4/2.5: embed and persist chunks in the local Weaviate collection."""
    from langchain_weaviate import WeaviateVectorStore

    client = connect_weaviate()
    if client.collections.exists(COLLECTION):
        client.collections.delete(COLLECTION)
    store = WeaviateVectorStore.from_documents(
        documents=documents,
        embedding=langchain_embeddings(),
        client=client,
        index_name=COLLECTION,
        text_key="text",
    )
    return client, store


def verify_weaviate(store, question: str = "How often should enterprise assets be inventoried?") -> list[dict]:
    results = store.similarity_search_with_score(question, k=5)
    return [
        {"score": float(score), "page": document.metadata.get("page"), "text": document.page_content[:240]}
        for document, score in results
    ]


def run_analysis(pdf: Path = PDF) -> dict:
    started = time.perf_counter()
    elements = parse_hi_res(pdf)
    chunks = chunk_comparison(elements)
    report = {
        "parser": "unstructured-hi_res",
        "source": pdf.name,
        "elements": element_report(elements),
        "chunking": chunk_report(chunks),
        "selected_chunker": "by_title",
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "embedding_dimensions": 384,
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    cache = STATE / "unstructured_chunks.json"
    cache.write_text(json.dumps([{"text": d.page_content, "metadata": d.metadata} for d in chunks["by_title"]], ensure_ascii=False), encoding="utf-8")
    return report


def load_selected_chunks() -> list[Document]:
    payload = json.loads((STATE / "unstructured_chunks.json").read_text(encoding="utf-8"))
    return [Document(page_content=item["text"], metadata=item["metadata"]) for item in payload]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["analyze", "weaviate"])
    args = parser.parse_args()
    if args.stage == "analyze":
        print(json.dumps(run_analysis(), indent=2))
    else:
        client, vector_store = store_in_weaviate(load_selected_chunks())
        try:
            print(json.dumps(verify_weaviate(vector_store), indent=2))
        finally:
            client.close()
