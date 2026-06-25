import numpy as np

from rag.pipeline.chunking import Chunk
from rag.pipeline.embeddings.base import EmbeddingModel
from rag.pipeline.indexing.base import VectorStore
from .base import RetrievalStrategy


class DenseRetrieval(RetrievalStrategy):
    def __init__(self, vector_store: VectorStore, embedding_model: EmbeddingModel):
        self._store = vector_store
        self._embed = embedding_model

    def retrieve(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        query_emb = self._embed.embed_query(query)
        return self._store.search(query_emb, k)

    def name(self) -> str:
        return "dense"
