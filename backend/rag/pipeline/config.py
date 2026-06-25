from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ChunkingConfig:
    strategy: Literal["recursive", "semantic", "hierarchical"] = "recursive"
    chunk_size: int = 512
    chunk_overlap: int = 64
    semantic_split_threshold: float = 0.5
    hierarchical_big_chunk_size: int = 1024
    hierarchical_small_chunk_size: int = 256


@dataclass
class EmbeddingConfig:
    model_name: str = "all-MiniLM-L6-v2"
    device: str = "cpu"


@dataclass
class IndexingConfig:
    vector_store: Literal["faiss"] = "faiss"
    index_dir: str = "index_cache"


@dataclass
class PipelineConfig:
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    indexing: IndexingConfig = field(default_factory=IndexingConfig)
