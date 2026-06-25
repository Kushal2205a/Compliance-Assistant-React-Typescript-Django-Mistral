from abc import ABC, abstractmethod

from rag.pipeline.chunking import Chunk


class RetrievalStrategy(ABC):
    @abstractmethod
    def retrieve(self, query: str, k: int) -> list[tuple[Chunk, float]]:
        pass

    @abstractmethod
    def name(self) -> str:
        pass
