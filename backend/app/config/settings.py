from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://compliance:compliance@localhost:5432/compliance"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "compliance_evidence"

    nvidia_api_key: str = ""
    llm_model: str = "nvidia/nemotron-nano-12b-v2-vl"
    llm_base_url: str | None = None

    storage_dir: str = "storage"

    cors_origins: str = "http://localhost:3000"

    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_device: str = "cpu"

    chunk_strategy: str = "compliance"
    chunk_size: int = 512
    chunk_overlap: int = 64

    retrieval_top_k: int = 5
    retrieval_hybrid: bool = False
    retrieval_hybrid_alpha: float = 0.7

    agent_max_retries: int = 2
    agent_max_hops: int = 3
    generation_max_tokens: int = 2048
    generation_max_context: int = 3000

    observability_enabled: bool = True

    model_config = {"env_prefix": "", "case_sensitive": False}


settings = Settings()
