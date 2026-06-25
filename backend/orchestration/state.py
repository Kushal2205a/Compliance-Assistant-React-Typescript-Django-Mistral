from dataclasses import dataclass, field
from typing import Any

from rag.pipeline.chunking import Chunk
from rag.pipeline.observability.tracker import ExecutionTrace
from rag.pipeline.routing.router import RouterDecision


@dataclass
class AgentState:
    query: str = ""
    original_query: str = ""
    router_decision: RouterDecision | None = None
    transformed_queries: list[str] = field(default_factory=list)
    active_query: str = ""
    retrieved_chunks: list[Chunk] = field(default_factory=list)
    chunk_scores: list[float] = field(default_factory=list)
    assembled_context: str = ""
    retry_count: int = 0
    hop_count: int = 0
    max_retries: int = 2
    max_hops: int = 3
    context_sufficient: bool = False
    missing_info: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    reformulated_query: str | None = None
    tool_calls: list[dict] = field(default_factory=list)
    reasoning_steps: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    generation: str = ""
    trace: ExecutionTrace | None = None
    router_llm: Any = None
    retrieval_service: Any = None
    generation_llm: Any = None
    generation_kwargs: dict = field(default_factory=dict)
