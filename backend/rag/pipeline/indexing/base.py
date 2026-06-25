from abc import ABC, abstractmethod

import numpy as np

from ..chunking import Chunk


class VectorStore(ABC):
    @abstractmethod
    def add(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        pass

    @abstractmethod
    def search(
        self, query_embedding: np.ndarray, k: int
    ) -> list[tuple[Chunk, float]]:
        pass

    @abstractmethod
    def remove(self, chunk_ids: list[str]) -> None:
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        pass

    @classmethod
    @abstractmethod
    def load(cls, path: str, chunks: list[Chunk]) -> "VectorStore":
        pass

    @abstractmethod
    def clear(self) -> None:
        pass
