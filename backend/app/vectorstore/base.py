from abc import ABC, abstractmethod

import numpy as np


class ChunkData:
    id: str
    document_id: str
    content: str
    metadata: dict

    def __init__(self, id: str, document_id: str, content: str, metadata: dict | None = None):
        self.id = id
        self.document_id = document_id
        self.content = content
        self.metadata = metadata or {}


class SearchResult:
    chunk: ChunkData
    score: float

    def __init__(self, chunk: ChunkData, score: float):
        self.chunk = chunk
        self.score = score


class VectorStore(ABC):
    @abstractmethod
    def add(self, chunks: list[ChunkData], embeddings: np.ndarray) -> None:
        pass

    @abstractmethod
    def search(self, query_embedding: np.ndarray, k: int) -> list[SearchResult]:
        pass

    @abstractmethod
    def delete(self, chunk_ids: list[str]) -> None:
        pass

    @abstractmethod
    def count(self) -> int:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
