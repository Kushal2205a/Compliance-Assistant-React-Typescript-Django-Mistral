ROUTE_PROMPT = """Classify the following user query into exactly one category:

- simple_lookup: Asking for specific information that can be found directly in a document
- multi_part: Contains multiple distinct questions combined together
- comparison: Asking to compare or contrast two or more items
- analytical: Requires synthesis, analysis, or drawing conclusions from multiple sources
- no_retrieval: Greeting, chit-chat, thanks, or anything not requiring document search

Query: {query}

Respond with a JSON object:
{{"type": "<category>", "sub_queries": ["<list of sub-questions if multi_part, otherwise the original query>"], "reasoning": "<brief explanation>"}}"""
