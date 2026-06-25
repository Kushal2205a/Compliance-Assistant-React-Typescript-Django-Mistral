from ..config import ChunkingConfig
from . import Chunk
from .strategies import (
    compliance_chunker,
    document_aware_chunker,
    hierarchical_chunker,
    recursive_chunker,
    semantic_chunker,
    sentence_chunker,
)


class ChunkingService:
    def __init__(self, config: ChunkingConfig):
        self.config = config

    def chunk(self, text: str, document_id: str, page_map: dict[int, int] | None = None) -> list[Chunk]:
        strategy = self.config.strategy
        print(f"[chunker] strategy={strategy}, text_len={len(text)}, page_map={len(page_map) if page_map else 0} pages")
        if strategy == "document_aware":
            result = document_aware_chunker(
                text,
                document_id,
                chunk_size=self.config.chunk_size,
                overlap=self.config.chunk_overlap,
                page_map=page_map,
            )
        elif strategy == "recursive":
            result = recursive_chunker(
                text, document_id, self.config.chunk_size, self.config.chunk_overlap
            )
        elif strategy == "sentence":
            result = sentence_chunker(text, document_id, self.config.chunk_size)
        elif strategy == "compliance":
            result = compliance_chunker(text, document_id)
        else:
            result = recursive_chunker(
                text, document_id, self.config.chunk_size, self.config.chunk_overlap
            )
        print(f"[chunker] created {len(result)} chunks")
        return result

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
