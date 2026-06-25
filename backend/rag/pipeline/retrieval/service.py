from rag.pipeline.chunking import Chunk
from rag.pipeline.embeddings.base import EmbeddingModel
from rag.pipeline.indexing.base import VectorStore
from rag.pipeline.indexing.service import IndexResult, IndexingService

from .strategies import RetrievalStrategy
from .strategies.dense import DenseRetrieval
from .strategies.hybrid import HybridRetrieval


class RetrievalService:
    def __init__(
        self,
        indexing_service: IndexingService,
        embedding_model: EmbeddingModel,
        enable_hybrid: bool = False,
        hybrid_alpha: float = 0.7,
    ):
        self._indexing = indexing_service
        self._embed = embedding_model
        self._enable_hybrid = enable_hybrid
        self._hybrid_alpha = hybrid_alpha
        self._strategies: dict[str, RetrievalStrategy] = {}
        self._current_store: VectorStore | None = None

    def _ensure_strategies(self, store: VectorStore) -> None:
        if store is self._current_store:
            return
        self._current_store = store
        self._strategies = {
            "dense": DenseRetrieval(store, self._embed),
        }
        if self._enable_hybrid:
            self._strategies["hybrid"] = HybridRetrieval(
                store, self._embed, self._hybrid_alpha
            )

    def index(self, file, document_id: str | None = None, progress_callback=None) -> IndexResult:
        return self._indexing.index_document(file, document_id, progress_callback)

    def search(
        self,
        result: IndexResult,
        query: str,
        k: int = 5,
        strategy: str = "dense",
    ) -> list[tuple[Chunk, float]]:
        self._ensure_strategies(result.vector_store)
        strat = self._strategies.get(strategy, self._strategies["dense"])
        return strat.retrieve(query, k)

    def get_chunk_texts(self, results: list[tuple[Chunk, float]]) -> list[str]:
        return [c.content for c, _ in results]

    def get_parent_chunks(self, results: list[tuple[Chunk, float]]) -> list[tuple[Chunk, float]]:
        parent_ids = set()
        for chunk, score in results:
            pid = chunk.metadata.get("parent_id")
            if pid:
                parent_ids.add(pid)
        expanded: list[tuple[Chunk, float]] = list(results)
        if self._current_store:
            for chunk in self._current_store.chunks:
                if chunk.id in parent_ids:
                    expanded.append((chunk, 1.0))
        return expanded
