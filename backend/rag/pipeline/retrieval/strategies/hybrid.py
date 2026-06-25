import numpy as np

from rag.pipeline.chunking import Chunk
from rag.pipeline.embeddings.base import EmbeddingModel
from rag.pipeline.indexing.base import VectorStore
from .base import RetrievalStrategy


class BM25:
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_count = 0
        self.avg_dl = 0.0
        self.df: dict[str, int] = {}
        self.doc_lens: list[int] = []
        self.doc_tokens: list[list[str]] = []

    def fit(self, texts: list[str]) -> None:
        self.doc_tokens = [t.split() for t in texts]
        self.doc_count = len(texts)
        self.doc_lens = [len(t) for t in self.doc_tokens]
        self.avg_dl = sum(self.doc_lens) / max(self.doc_count, 1)
        self.df = {}
        for tokens in self.doc_tokens:
            for token in set(tokens):
                self.df[token] = self.df.get(token, 0) + 1

    def score(self, query_tokens: list[str], doc_idx: int) -> float:
        score = 0.0
        doc_tokens = self.doc_tokens[doc_idx]
        dl = self.doc_lens[doc_idx]
        for token in query_tokens:
            if token not in self.df:
                continue
            tf = doc_tokens.count(token)
            idf = np.log(
                (self.doc_count - self.df[token] + 0.5) / (self.df[token] + 0.5) + 1.0
            )
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
            score += idf * numerator / denominator
        return score

    def search(self, query: str, k: int) -> list[tuple[int, float]]:
        query_tokens = query.lower().split()
        scores = [
            (i, self.score(query_tokens, i)) for i in range(self.doc_count)
        ]
        scores.sort(key=lambda x: -x[1])
        return scores[:k]


class HybridRetrieval(RetrievalStrategy):
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_model: EmbeddingModel,
        alpha: float = 0.7,
    ):
        self._store = vector_store
        self._embed = embedding_model
        self._alpha = alpha
        self._bm25 = BM25()
        if vector_store.chunks:
            self._bm25.fit([c.content for c in vector_store.chunks])

    def _rebuild_bm25(self) -> None:
        if self._store.chunks:
            self._bm25.fit([c.content for c in self._store.chunks])

    def retrieve(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        self._rebuild_bm25()

        # Dense
        query_emb = self._embed.embed_query(query)
        dense_results = self._store.search(query_emb, k * 2)

        # Sparse
        bm25_results = self._bm25.search(query, k * 2)

        chunk_map = {c.id: (c, i) for i, c in enumerate(self._store.chunks)}
        dense_scores: dict[str, float] = {}
        for chunk, score in dense_results:
            dense_scores[chunk.id] = float(score)
        sparse_scores: dict[str, float] = {}
        for idx, score in bm25_results:
            chunk = self._store.chunks[idx]
            sparse_scores[chunk.id] = float(score)

        all_ids = set(dense_scores) | set(sparse_scores)
        max_dense = max(dense_scores.values()) if dense_scores else 1.0
        max_sparse = max(sparse_scores.values()) if sparse_scores else 1.0

        combined: list[tuple[str, float]] = []
        for cid in all_ids:
            d_score = dense_scores.get(cid, 0.0) / max_dense
            s_score = sparse_scores.get(cid, 0.0) / max_sparse
            combined.append((cid, self._alpha * d_score + (1 - self._alpha) * s_score))

        combined.sort(key=lambda x: -x[1])
        results: list[tuple[Chunk, float]] = []
        for cid, score in combined[:k]:
            if cid in chunk_map:
                results.append((chunk_map[cid][0], score))
        return results

    def name(self) -> str:
        return "hybrid"
