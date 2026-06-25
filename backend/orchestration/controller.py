from langgraph.graph import END, StateGraph

from orchestration.nodes.analyze import analyze_query, transform_query
from orchestration.nodes.evaluate import evaluate_context
from orchestration.nodes.generate import assemble_context, generate_response
from orchestration.nodes.retrieve import retrieve_documents
from orchestration.state import AgentState


def should_continue(state: AgentState) -> str:
    if state.router_decision and state.router_decision.query_type == "no_retrieval":
        return "assemble"

    if state.context_sufficient:
        return "assemble"

    if state.retry_count < state.max_retries:
        return "reformulate"

    return "assemble"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("analyze", analyze_query)
    graph.add_node("transform", transform_query)
    graph.add_node("retrieve", retrieve_documents)
    graph.add_node("evaluate", evaluate_context)
    graph.add_node("assemble", assemble_context)
    graph.add_node("generate", generate_response)

    graph.set_entry_point("analyze")

    graph.add_edge("analyze", "transform")
    graph.add_edge("transform", "retrieve")
    graph.add_edge("retrieve", "evaluate")

    graph.add_conditional_edges(
        "evaluate",
        should_continue,
        {
            "assemble": "assemble",
            "reformulate": "retrieve",
        },
    )

    graph.add_edge("assemble", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


default_graph = build_graph()
