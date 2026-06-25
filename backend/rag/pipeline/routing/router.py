from dataclasses import dataclass, field

from llm import LLMProvider

from ..prompts import ROUTE_PROMPT

QUERY_TYPES = [
    "simple_lookup",
    "multi_part",
    "comparison",
    "analytical",
    "no_retrieval",
]


@dataclass
class RouterDecision:
    query_type: str
    sub_queries: list[str] = field(default_factory=list)
    reasoning: str = ""


def classify_query(query: str, llm: LLMProvider | None = None) -> RouterDecision:
    if not llm:
        return RouterDecision(query_type="simple_lookup", sub_queries=[query])

    prompt = ROUTE_PROMPT.format(query=query)
    response = llm.invoke(
        [
            {"role": "system", "content": "You are a query routing assistant. Return ONLY a JSON object with keys: type, sub_queries (array), reasoning."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
    )
    return _parse_route_response(response, query)


def _parse_route_response(response: str, original_query: str) -> RouterDecision:
    import json
    import re

    json_match = re.search(r"\{.*\}", response, re.DOTALL)
    if not json_match:
        return RouterDecision(query_type="simple_lookup", sub_queries=[original_query])

    try:
        data = json.loads(json_match.group())
        qtype = data.get("type", "simple_lookup")
        if qtype not in QUERY_TYPES:
            qtype = "simple_lookup"
        subs = data.get("sub_queries", [original_query])
        if not subs:
            subs = [original_query]
        return RouterDecision(
            query_type=qtype,
            sub_queries=subs,
            reasoning=data.get("reasoning", ""),
        )
    except (json.JSONDecodeError, KeyError):
        return RouterDecision(query_type="simple_lookup", sub_queries=[original_query])
