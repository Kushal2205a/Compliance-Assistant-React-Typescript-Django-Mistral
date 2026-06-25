import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TraceStep:
    step: str
    input: Any = None
    output: Any = None
    latency: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class ExecutionTrace:
    query: str = ""
    router_decision: str = ""
    transformations: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    retry_count: int = 0
    hop_count: int = 0
    retrieved_docs: list[dict] = field(default_factory=list)
    final_context_size: int = 0
    total_latency: float = 0.0
    generation_latency: float = 0.0
    steps: list[TraceStep] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "router_decision": self.router_decision,
            "transformations": self.transformations,
            "tool_calls": self.tool_calls,
            "retry_count": self.retry_count,
            "hop_count": self.hop_count,
            "retrieved_doc_count": len(self.retrieved_docs),
            "final_context_size": self.final_context_size,
            "total_latency_s": round(self.total_latency, 3),
            "generation_latency_s": round(self.generation_latency, 3),
            "steps": [
                {
                    "step": s.step,
                    "latency_s": round(s.latency, 3),
                    "metadata": s.metadata,
                }
                for s in self.steps
            ],
            "errors": self.errors,
        }


class Tracker:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.trace = ExecutionTrace()
        self._start = 0.0
        self._step_start = 0.0

    def start(self, query: str) -> None:
        if not self.enabled:
            return
        self.trace = ExecutionTrace(query=query)
        self._start = time.time()

    def begin_step(self, name: str, **meta: Any) -> None:
        if not self.enabled:
            return
        self._step_start = time.time()
        self.trace.steps.append(
            TraceStep(step=name, metadata=meta, input=meta.get("input"))
        )

    def end_step(self, output: Any = None) -> None:
        if not self.enabled:
            return
        if self.trace.steps:
            self.trace.steps[-1].latency = time.time() - self._step_start
            self.trace.steps[-1].output = output

    def record_tool_call(self, tool: str, query: str, doc_count: int, latency: float) -> None:
        if not self.enabled:
            return
        self.trace.tool_calls.append(
            {"tool": tool, "query": query, "doc_count": doc_count, "latency_s": round(latency, 3)}
        )

    def record_retrieval(self, chunks: list) -> None:
        if not self.enabled:
            return
        for c in chunks:
            self.trace.retrieved_docs.append(
                {"id": c.id, "doc_id": c.document_id, "preview": c.content[:120]}
            )

    def record_error(self, error: str) -> None:
        if not self.enabled:
            return
        self.trace.errors.append(error)

    def finish(self) -> ExecutionTrace:
        if not self.enabled:
            return self.trace
        self.trace.total_latency = time.time() - self._start
        return self.trace

    def reset(self) -> None:
        self.trace = ExecutionTrace()
        self._start = 0.0
