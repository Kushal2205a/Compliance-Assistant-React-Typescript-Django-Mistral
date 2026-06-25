import time

from orchestration.state import AgentState
from rag.pipeline.routing.router import classify_query
from rag.pipeline.prompts import REWRITE_PROMPT


def analyze_query(state: AgentState) -> dict:
    start = time.time()
    decision = classify_query(state.query, state.router_llm)
    elapsed = time.time() - start

    state.router_decision = decision
    state.reasoning_steps.append(f"Router: {decision.query_type} ({decision.reasoning})")

    if state.trace:
        state.trace.router_decision = decision.query_type

    active = state.query
    if decision.sub_queries:
        active = decision.sub_queries[0]

    state.active_query = active
    state.transformed_queries = [active]

    return {
        "router_decision": decision,
        "active_query": active,
        "transformed_queries": [active],
        "reasoning_steps": state.reasoning_steps,
    }


def transform_query(state: AgentState) -> dict:
    if state.router_decision and state.router_decision.query_type == "no_retrieval":
        return {}

    llm = state.router_llm
    if not llm:
        return {}

    prompt = REWRITE_PROMPT.format(query=state.active_query)
    rewritten = llm.invoke(
        [
            {"role": "system", "content": "Rewrite the query to improve retrieval accuracy. Return ONLY the rewritten query."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    ).strip()

    if rewritten:
        state.transformed_queries.append(rewritten)
        state.active_query = rewritten
        state.reasoning_steps.append(f"Rewritten: {rewritten[:80]}...")

    if state.trace:
        state.trace.transformations = state.transformed_queries

    return {
        "active_query": state.active_query,
        "transformed_queries": state.transformed_queries,
        "reasoning_steps": state.reasoning_steps,
    }
