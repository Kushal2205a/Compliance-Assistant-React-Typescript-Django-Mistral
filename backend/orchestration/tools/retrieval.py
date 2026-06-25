import time
from typing import Any

from rag.pipeline.chunking import Chunk
from rag.pipeline.retrieval.service import RetrievalService


class RetrievalTool:
    def __init__(self, retrieval_service: RetrievalService):
        self._service = retrieval_service
        self._index_result = None

    def set_index_result(self, result) -> None:
        self._index_result = result

    def search(
        self,
        query: str,
        k: int = 5,
        strategy: str = "dense",
        expand_parents: bool = False,
    ) -> dict[str, Any]:
        if self._index_result is None:
            return {"chunks": [], "scores": [], "latency": 0.0}
        start = time.time()
        results = self._service.search(self._index_result, query, k, strategy)
        latency = time.time() - start
        chunks = [c for c, _ in results]
        scores = [float(s) for _, s in results]

        if expand_parents:
            expanded = self._service.get_parent_chunks(results)
            chunks = [c for c, _ in expanded]
            scores = [float(s) for _, s in expanded]

        return {
            "chunks": chunks,
            "scores": scores,
            "latency": round(latency, 3),
            "strategy": strategy,
            "count": len(chunks),
        }

    def get_chunk_texts(self, chunks: list[Chunk]) -> list[str]:
        return self._service.get_chunk_texts([(c, 0.0) for c in chunks])
