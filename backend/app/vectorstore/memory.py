import numpy as np

from .base import ChunkData, SearchResult, VectorStore


class InMemoryVectorStore(VectorStore):
    def __init__(self):
        self._chunks: list[ChunkData] = []
        self._embeddings: list[np.ndarray] = []

    def add(self, chunks: list[ChunkData], embeddings: np.ndarray) -> None:
        if not chunks or embeddings.shape[0] == 0:
            return
        for chunk, emb in zip(chunks, embeddings):
            self._chunks.append(chunk)
            self._embeddings.append(emb)

    def search(self, query_embedding: np.ndarray, k: int) -> list[SearchResult]:
        if not self._embeddings:
            return []
        q = query_embedding.flatten()
        if q.ndim != 1 or q.shape[0] == 0:
            return []
        scores = []
        for emb in self._embeddings:
            e = emb.flatten()
            if e.ndim != 1 or e.shape != q.shape:
                continue
            score = float(np.dot(q, e))
            scores.append(score)
        if not scores:
            return []
        indices = np.argsort(scores)[::-1][:k]
        results = []
        for idx in indices:
            results.append(SearchResult(chunk=self._chunks[idx], score=scores[idx]))
        return results

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[ChunkData]:
        id_set = set(chunk_ids)
        return [c for c in self._chunks if c.id in id_set]

    def delete(self, chunk_ids: list[str]) -> None:
        ids_set = set(chunk_ids)
        remaining = [(c, e) for c, e in zip(self._chunks, self._embeddings) if c.id not in ids_set]
        self._chunks = [c for c, _ in remaining]
        self._embeddings = [e for _, e in remaining]

    def delete_by_document(self, document_id: str) -> None:
        remaining = [(c, e) for c, e in zip(self._chunks, self._embeddings) if c.document_id != document_id]
        self._chunks = [c for c, _ in remaining]
        self._embeddings = [e for _, e in remaining]

    def count(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        self._chunks.clear()
        self._embeddings.clear()
