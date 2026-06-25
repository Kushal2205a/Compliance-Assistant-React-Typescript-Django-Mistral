import json
import os
import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from app.config.settings import settings


class BM25Index:
    """BM25 index for lexical retrieval of compliance evidence.

    Built on top of rank_bm25. Index is persisted to disk as a pickle
    and rebuilt when the underlying chunk set changes.
    """

    def __init__(self):
        self._index: BM25Okapi | None = None
        self._documents: list[dict] = []
        self._tokenized: list[list[str]] = []
        self._loaded: bool = False
        self._path = Path(settings.abs_storage_dir) / settings.bm25_index_dir

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def build(self, chunks: list) -> None:
        """Build BM25 index from a list of chunk objects (must have .content and .id)."""
        self._documents = []
        self._tokenized = []
        for chunk in chunks:
            content = chunk.content if hasattr(chunk, "content") else chunk.get("content", "")
            doc_id = chunk.id if hasattr(chunk, "id") else chunk.get("id", "")
            tokens = self._tokenize(content)
            if not tokens:
                continue
            self._tokenized.append(tokens)
            self._documents.append({"id": doc_id, "content": content})

        if self._tokenized:
            self._index = BM25Okapi(self._tokenized)
        else:
            self._index = None

        self._persist()

    def search(self, query: str, top_k: int | None = None) -> list[tuple[str, float]]:
        """Search index. Returns list of (doc_id, score)."""
        if self._index is None:
            return []
        k = top_k or settings.retrieval_bm25_top_k
        tokens = self._tokenize(query)
        scores = self._index.get_scores(tokens)
        scored = [(self._documents[i]["id"], float(scores[i])) for i in range(len(scores))]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def count(self) -> int:
        return len(self._documents)

    def clear(self) -> None:
        self._index = None
        self._documents = []
        self._tokenized = []
        self._loaded = False
        if self._path.exists():
            import shutil
            shutil.rmtree(self._path)

    def _persist(self) -> None:
        self._path.mkdir(parents=True, exist_ok=True)
        with open(self._path / "index.pkl", "wb") as f:
            pickle.dump({
                "documents": self._documents,
                "tokenized": self._tokenized,
            }, f)

    def load(self) -> bool:
        meta = self._path / "index.pkl"
        if not meta.exists():
            return False
        try:
            with open(meta, "rb") as f:
                data = pickle.load(f)
            self._documents = data["documents"]
            self._tokenized = data["tokenized"]
            if self._tokenized:
                self._index = BM25Okapi(self._tokenized)
            self._loaded = True
            return True
        except Exception:
            return False


_bm25_instance: BM25Index | None = None


def get_bm25_index() -> BM25Index:
    global _bm25_instance
    if _bm25_instance is None:
        _bm25_instance = BM25Index()
        _bm25_instance.load()
    return _bm25_instance


def reset_bm25_index() -> None:
    global _bm25_instance
    _bm25_instance = None
