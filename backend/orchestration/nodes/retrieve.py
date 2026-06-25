import time

from orchestration.state import AgentState
from orchestration.tools.retrieval import RetrievalTool


def retrieve_documents(state: AgentState) -> dict:
    tool: RetrievalTool = state.retrieval_service
    if tool is None:
        return {"errors": ["No retrieval tool available"]}

    query = state.reformulated_query or state.active_query
    strategy = "dense"
    if state.router_decision:
        qtype = state.router_decision.query_type
        if qtype in ("comparison", "analytical"):
            strategy = "dense"
        elif qtype == "simple_lookup":
            strategy = "dense"

    result = tool.search(
        query=query,
        k=5,
        strategy=strategy,
        expand_parents=(state.retry_count > 0),
    )

    chunks: list = result["chunks"]
    scores: list[float] = result["scores"]

    state.retrieved_chunks = chunks
    state.chunk_scores = scores
    state.hop_count += 1
    state.reformulated_query = None

    state.reasoning_steps.append(
        f"Retrieved {len(chunks)} chunks via {strategy} (hop {state.hop_count})"
    )

    if state.trace:
        state.trace.record_tool_call(strategy, query, len(chunks), result["latency"])
        state.trace.record_retrieval(chunks)
        state.trace.hop_count = state.hop_count

    return {
        "retrieved_chunks": chunks,
        "chunk_scores": scores,
        "hop_count": state.hop_count,
        "reasoning_steps": state.reasoning_steps,
    }
