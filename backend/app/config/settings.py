import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://compliance:compliance@localhost:5432/compliance"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "compliance_evidence"

    nvidia_api_key: str = ""
    llm_model: str = "nvidia/nemotron-nano-12b-v2-vl"
    llm_base_url: str | None = None

    storage_dir: str = "storage"

    @property
    def abs_storage_dir(self) -> str:
        return os.path.abspath(self.storage_dir)

    cors_origins: str = "http://localhost:3000"

    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"

    chunk_strategy: str = "document_aware"
    chunk_size: int = 512
    chunk_overlap: int = 64
    indexing_version: int = 2

    retrieval_top_k: int = 5
    retrieval_dense_top_k: int = 20
    retrieval_bm25_top_k: int = 15
    retrieval_rrf_k: int = 60
    retrieval_rrf_top_k: int = 10

    bm25_enabled: bool = True
    bm25_index_dir: str = "bm25_index"

    reranker_enabled: bool = True
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_top_k: int = 5

    context_expansion_enabled: bool = True
    context_expansion_window: int = 2

    adaptive_retrieval_enabled: bool = True
    adaptive_max_retries: int = 2

    boilerplate_filter_enabled: bool = True
    boilerplate_min_length: int = 50

    evidence_formatter_enabled: bool = True
    evidence_formatter_max_context: int = 3000

    agent_max_retries: int = 2
    agent_max_hops: int = 3
    generation_max_tokens: int = 2048
    generation_max_context: int = 3000

    observability_enabled: bool = True

    evaluation_mode: str = "domain"
    batch_size: int = 5
    control_groups_path: str = "config/groups_default.json"

    model_config = {"env_prefix": "", "case_sensitive": False, "env_file": ".env"}


settings = Settings()
