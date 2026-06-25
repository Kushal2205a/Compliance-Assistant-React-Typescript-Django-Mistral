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
    provider: Literal["nvidia"] = "nvidia"
    model: str = "nvidia/nemotron-3-super-120b-a12b"
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

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        import os

        llm_model = os.getenv("LLM_MODEL", "nvidia/nemotron-3-super-120b-a12b")
        llm_base_url = os.getenv("LLM_BASE_URL") or None
        nvidia_key = os.getenv("NVIDIA_API_KEY") or None

        return cls(
            llm=LLMConfig(
                provider="nvidia",
                model=llm_model,
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.0")),
                base_url=llm_base_url,
                api_key=nvidia_key,
            ),
            chunking=ChunkingConfig(
                strategy=os.getenv("CHUNK_STRATEGY", "compliance"),
                chunk_size=int(os.getenv("CHUNK_SIZE", "512")),
                chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "64")),
            ),
            embedding=EmbeddingConfig(
                model_name=os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            ),
            indexing=IndexingConfig(
                index_dir=os.getenv("INDEX_DIR", "index_cache"),
            ),
            routing=RoutingConfig(
                enabled=os.getenv("ROUTING_ENABLED", "true").lower() == "true",
            ),
            retrieval=RetrievalConfig(
                top_k=int(os.getenv("RETRIEVAL_TOP_K", "5")),
                enable_hybrid=os.getenv("RETRIEVAL_HYBRID", "false").lower() == "true",
                hybrid_alpha=float(os.getenv("RETRIEVAL_HYBRID_ALPHA", "0.7")),
            ),
            generation=GenerationConfig(
                max_context_len=int(os.getenv("GENERATION_MAX_CONTEXT", "3000")),
                max_tokens=int(os.getenv("GENERATION_MAX_TOKENS", "2048")),
            ),
            agent=AgentConfig(
                max_retries=int(os.getenv("AGENT_MAX_RETRIES", "2")),
                max_hops=int(os.getenv("AGENT_MAX_HOPS", "3")),
            ),
            observability=ObservabilityConfig(
                enabled=os.getenv("OBSERVABILITY_ENABLED", "true").lower() == "true",
            ),
        )
