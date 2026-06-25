from dataclasses import dataclass, field
from typing import Any

from llm.base import LLMProvider
from llm.factory import create_llm
from orchestration.controller import default_graph
from orchestration.state import AgentState
from orchestration.tools.retrieval import RetrievalTool
from rag.pipeline.config import PipelineConfig
from rag.pipeline.indexing.service import IndexingService
from rag.pipeline.observability.tracker import ExecutionTrace, Tracker
from rag.pipeline.retrieval.service import RetrievalService


@dataclass
class OrchestrationResult:
    response: str = ""
    trace: ExecutionTrace | None = None
    errors: list[str] = field(default_factory=list)


class OrchestrationService:
    def __init__(self, config: PipelineConfig):
        self._config = config
        self._indexing = IndexingService(config)
        self._embedding_model = self._indexing.embedding_model
        self._retrieval_svc = RetrievalService(
            self._indexing,
            self._embedding_model,
            enable_hybrid=config.retrieval.enable_hybrid,
            hybrid_alpha=config.retrieval.hybrid_alpha,
        )
        self._retrieval_tool = RetrievalTool(self._retrieval_svc)
        self._router_llm: LLMProvider | None = self._build_llm(
            config.routing.provider or config.llm.provider,
            config.routing.model or config.llm.model,
            config.llm.base_url,
            config.llm.api_key,
        )
        self._generation_llm: LLMProvider | None = self._build_llm(
            config.generation.provider or config.llm.provider,
            config.generation.model or config.llm.model,
            config.llm.base_url,
            config.llm.api_key,
        )
        self._tracker = Tracker(config.observability.enabled)

    def _build_llm(
        self,
        provider: str | None,
        model: str | None,
        base_url: str | None,
        api_key: str | None,
    ) -> LLMProvider | None:
        if provider and model:
            return create_llm(provider, model, base_url, api_key)
        return None

    def process_query(self, query: str, pdf_file, document_id: str | None = None) -> OrchestrationResult:
        self._tracker.start(query)

        try:
            result = self._retrieval_svc.index(pdf_file, document_id)
            self._retrieval_tool.set_index_result(result)

            state = AgentState(
                query=query,
                original_query=query,
                max_retries=self._config.agent.max_retries,
                max_hops=self._config.agent.max_hops,
                router_llm=self._router_llm,
                retrieval_service=self._retrieval_tool,
                generation_llm=self._generation_llm,
                generation_kwargs={
                    "temperature": self._config.generation.temperature or self._config.llm.temperature,
                    "max_tokens": self._config.generation.max_tokens,
                },
                trace=self._tracker.trace,
            )

            final = default_graph.invoke(state)
            trace = self._tracker.finish()

            return OrchestrationResult(
                response=final.get("generation", ""),
                trace=trace,
                errors=final.get("errors", []),
            )

        except Exception as e:
            self._tracker.record_error(str(e))
            trace = self._tracker.finish()
            return OrchestrationResult(
                response=f"Error processing query: {e}",
                trace=trace,
                errors=[str(e)],
            )
