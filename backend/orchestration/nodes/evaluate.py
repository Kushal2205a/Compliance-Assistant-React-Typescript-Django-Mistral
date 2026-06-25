import json
import re

from orchestration.state import AgentState
from rag.pipeline.prompts import EVALUATE_PROMPT


def evaluate_context(state: AgentState) -> dict:
    llm = state.router_llm
    if not llm:
        state.context_sufficient = True
        return {"context_sufficient": True}

    chunks = state.retrieved_chunks
    if not chunks:
        state.context_sufficient = False
        state.reasoning_steps.append("No chunks retrieved, insufficient context")
        return {"context_sufficient": False}

    context = "\n\n".join(c.content[:500] for c in chunks[:3])

    if not context.strip():
        state.context_sufficient = False
        return {"context_sufficient": False}

    if state.router_decision and state.router_decision.query_type == "no_retrieval":
        state.context_sufficient = True
        return {"context_sufficient": True}

    prompt = EVALUATE_PROMPT.format(query=state.active_query, context=context)
    response = llm.invoke(
        [
            {
                "role": "system",
                "content": "You evaluate whether retrieved context is sufficient. Return ONLY a JSON object.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )

    result = _parse_eval(response)

    state.context_sufficient = result.get("sufficient", False)
    state.missing_info = result.get("missing_info", [])
    state.contradictions = result.get("contradictions", [])
    state.reformulated_query = result.get("reformulated_query", None)

    state.reasoning_steps.append(
        f"Evaluation: sufficient={state.context_sufficient}, "
        f"missing={state.missing_info[:2]}, "
        f"reformulated={'yes' if state.reformulated_query else 'no'}"
    )

    return {
        "context_sufficient": state.context_sufficient,
        "missing_info": state.missing_info,
        "contradictions": state.contradictions,
        "reformulated_query": state.reformulated_query,
        "reasoning_steps": state.reasoning_steps,
    }


def _parse_eval(response: str) -> dict:
    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if not json_match:
        return {"sufficient": True, "missing_info": [], "contradictions": []}
    try:
        return json.loads(json_match.group())
    except json.JSONDecodeError:
        return {"sufficient": True, "missing_info": [], "contradictions": []}
