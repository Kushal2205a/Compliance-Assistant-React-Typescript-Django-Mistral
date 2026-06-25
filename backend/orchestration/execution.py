from dataclasses import dataclass, field
from typing import Any


@dataclass
class QueryRecord:
    query: str
    transformed: str
    strategy: str
    doc_count: int
    latency: float


@dataclass
class ToolOutput:
    chunk_ids: list[str]
    previews: list[str]


@dataclass
class ExecutionHistory:
    queries: list[QueryRecord] = field(default_factory=list)
    tool_outputs: list[dict] = field(default_factory=list)
    retries: int = 0
    hops: int = 0
    decisions: list[str] = field(default_factory=list)

    def record_query(self, original: str, transformed: str, strategy: str, doc_count: int, latency: float) -> None:
        self.queries.append(
            QueryRecord(original, transformed, strategy, doc_count, latency)
        )

    def record_tool_output(self, tool: str, chunk_ids: list[str], previews: list[str]) -> None:
        self.tool_outputs.append(
            {"tool": tool, "chunk_ids": chunk_ids, "previews": previews[:3]}
        )

    def record_decision(self, decision: str) -> None:
        self.decisions.append(decision)

    def summary(self) -> dict[str, Any]:
        return {
            "total_queries": len(self.queries),
            "total_tool_calls": len(self.tool_outputs),
            "retries": self.retries,
            "hops": self.hops,
            "decisions": self.decisions,
        }
