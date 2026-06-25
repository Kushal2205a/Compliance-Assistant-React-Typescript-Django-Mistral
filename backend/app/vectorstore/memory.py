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
        scores = []
        for emb in self._embeddings:
            score = float(np.dot(query_embedding, emb))
            scores.append(score)
        indices = np.argsort(scores)[::-1][:k]
        results = []
        for idx in indices:
            results.append(SearchResult(chunk=self._chunks[idx], score=scores[idx]))
        return results

    def delete(self, chunk_ids: list[str]) -> None:
        ids_set = set(chunk_ids)
        remaining = [(c, e) for c, e in zip(self._chunks, self._embeddings) if c.id not in ids_set]
        self._chunks = [c for c, _ in remaining]
        self._embeddings = [e for _, e in remaining]

    def count(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        self._chunks.clear()
        self._embeddings.clear()
