import time

from orchestration.state import AgentState
from rag.pipeline.prompts import GENERATE_PROMPT


def assemble_context(state: AgentState) -> dict:
    chunks = state.retrieved_chunks
    seen = set()
    unique: list[str] = []
    for c in chunks:
        if c.content not in seen:
            seen.add(c.content)
            unique.append(c.content)

    context = "\n\n".join(unique)
    max_len = 3000
    if len(context) > max_len:
        context = context[:max_len].rsplit(" ", 1)[0]

    state.assembled_context = context

    if state.trace:
        state.trace.final_context_size = len(context)

    return {"assembled_context": context}


def generate_response(state: AgentState) -> dict:
    start = time.time()
    llm = state.generation_llm

    if not state.assembled_context or state.router_decision and state.router_decision.query_type == "no_retrieval":
        if llm:
            response = llm.invoke(
                [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": state.query},
                ],
                **state.generation_kwargs,
            )
        else:
            response = "Hello! I'm a compliance assistant. Please upload a document and ask a question."
        elapsed = time.time() - start
        return {"generation": response, "generation_latency": round(elapsed, 3)}

    if not llm:
        response = "No LLM configured for generation."
        elapsed = time.time() - start
        return {"generation": response, "generation_latency": round(elapsed, 3)}

    prompt = GENERATE_PROMPT.format(
        query=state.query,
        context=state.assembled_context,
    )

    response = llm.invoke(
        [
            {
                "role": "system",
                "content": "You are a compliance expert. Answer based ONLY on the provided context.",
            },
            {"role": "user", "content": prompt},
        ],
        **state.generation_kwargs,
    )

    state.generation = response
    elapsed = time.time() - start

    if state.trace:
        state.trace.generation_latency = elapsed

    return {"generation": response, "generation_latency": round(elapsed, 3)}
