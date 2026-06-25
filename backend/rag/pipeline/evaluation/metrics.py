from rag.pipeline.observability.tracker import ExecutionTrace


def precision_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for r in top_k if any(rel.lower() in r.lower() for rel in relevant))
    return hits / k


def recall_at_k(retrieved: list[str], relevant: list[str], k: int) -> float:
    top_k = retrieved[:k]
    if not relevant:
        return 1.0
    hits = sum(1 for r in top_k if any(rel.lower() in r.lower() for rel in relevant))
    return hits / len(relevant)


def mrr(retrieved: list[str], relevant: list[str]) -> float:
    for i, r in enumerate(retrieved):
        if any(rel.lower() in r.lower() for rel in relevant):
            return 1.0 / (i + 1)
    return 0.0


def average_tool_calls(traces: list[ExecutionTrace]) -> float:
    if not traces:
        return 0.0
    return sum(len(t.tool_calls) for t in traces) / len(traces)


def retry_rate(traces: list[ExecutionTrace]) -> float:
    if not traces:
        return 0.0
    return sum(1 for t in traces if t.retry_count > 0) / len(traces)


def successful_retrieval_rate(traces: list[ExecutionTrace]) -> float:
    if not traces:
        return 0.0
    successful = sum(1 for t in traces if t.retrieved_docs and not t.errors)
    return successful / len(traces)


def average_retrieval_latency(traces: list[ExecutionTrace]) -> float:
    if not traces:
        return 0.0
    latencies = [t.total_latency for t in traces if t.total_latency > 0]
    if not latencies:
        return 0.0
    return sum(latencies) / len(latencies)
