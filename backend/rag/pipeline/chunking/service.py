from ..config import ChunkingConfig
from . import Chunk
from .strategies import (
    compliance_chunker,
    hierarchical_chunker,
    recursive_chunker,
    semantic_chunker,
    sentence_chunker,
)


class ChunkingService:
    def __init__(self, config: ChunkingConfig):
        self.config = config

    def chunk(self, text: str, document_id: str) -> list[Chunk]:
        strategy = self.config.strategy
        if strategy == "recursive":
            return recursive_chunker(
                text, document_id, self.config.chunk_size, self.config.chunk_overlap
            )
        elif strategy == "sentence":
            return sentence_chunker(text, document_id, self.config.chunk_size)
        elif strategy == "compliance":
            return compliance_chunker(text, document_id)
        else:
            return recursive_chunker(
                text, document_id, self.config.chunk_size, self.config.chunk_overlap
            )

    def chunk_semantic(
        self, text: str, document_id: str, embed_fn
    ) -> list[Chunk]:
        return semantic_chunker(
            text,
            document_id,
            embed_fn,
            self.config.semantic_split_threshold,
        )

    def chunk_hierarchical(self, text: str, document_id: str) -> list[Chunk]:
        return hierarchical_chunker(
            text,
            document_id,
            self.config.hierarchical_big_chunk_size,
            self.config.hierarchical_small_chunk_size,
        )
