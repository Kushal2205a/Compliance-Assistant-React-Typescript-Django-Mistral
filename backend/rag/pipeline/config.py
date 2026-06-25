from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ChunkingConfig:
    strategy: Literal["recursive", "semantic", "hierarchical", "compliance"] = "recursive"
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
class LLMConfig:
    provider: Literal["ollama", "nvidia"] = "ollama"
    model: str = "mistral"
    temperature: float = 0.0
    max_tokens: int = 1024
    base_url: str | None = None
    api_key: str | None = None


@dataclass
class RoutingConfig:
    enabled: bool = True
    provider: str | None = None
    model: str | None = None


@dataclass
class RetrievalConfig:
    top_k: int = 5
    hybrid_alpha: float = 0.7
    enable_hybrid: bool = False
    min_score: float = 0.0


@dataclass
class GenerationConfig:
    provider: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int = 2048
    max_context_len: int = 3000
    stream: bool = True


@dataclass
class AgentConfig:
    max_retries: int = 2
    max_hops: int = 3
    provider: str | None = None
    model: str | None = None


@dataclass
class ObservabilityConfig:
    enabled: bool = True
    log_traces: bool = True


@dataclass
class PipelineConfig:
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    indexing: IndexingConfig = field(default_factory=IndexingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
