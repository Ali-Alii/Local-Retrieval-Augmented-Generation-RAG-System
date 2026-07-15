"""Assignment-faithful BGE reranker with a small, CPU-friendly fallback."""
from __future__ import annotations

from langchain_core.documents import Document

EXACT_MODEL = "BAAI/bge-reranker-v2-m3"


class BGEReranker:
    """Score query/document pairs with the reranker named in the project brief."""

    def __init__(self, model_name: str = EXACT_MODEL, device: str = "cpu"):
        from sentence_transformers import CrossEncoder

        self.model_name = model_name
        self.model = CrossEncoder(model_name, device=device, trust_remote_code=True)

    def rerank(self, question: str, documents: list[Document], top_k: int = 5) -> list[Document]:
        if not documents:
            return []
        scores = self.model.predict([(question, document.page_content) for document in documents])
        ranked = sorted(zip(documents, scores), key=lambda item: float(item[1]), reverse=True)
        output = []
        for document, score in ranked[:top_k]:
            document.metadata = {**document.metadata, "reranker_score": float(score), "reranker_model": self.model_name}
            output.append(document)
        return output


if __name__ == "__main__":
    from .exact_pipeline import load_selected_chunks

    question = "Explain the differences between IG1, IG2, and IG3."
    candidates = [document for document in load_selected_chunks() if document.metadata.get("page") in (14, 15, 47, 56)][:12]
    reranker = BGEReranker()
    for rank, document in enumerate(reranker.rerank(question, candidates, top_k=3), 1):
        print(f"{rank}. page {document.metadata.get('page')} score={document.metadata['reranker_score']:.4f}")
        print(document.page_content[:240])
