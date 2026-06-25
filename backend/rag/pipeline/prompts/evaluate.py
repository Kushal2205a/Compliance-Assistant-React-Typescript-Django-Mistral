EVALUATE_PROMPT = """You are evaluating whether the retrieved context is sufficient to answer the user's query.

Query: {query}

Retrieved Context:
{context}

Evaluate:
1. Does the context contain information relevant to the query?
2. Is any critical information missing?
3. Are there contradictions in the context?
4. Is the context specific enough, or is it too generic?

Respond with a JSON object:
{{"sufficient": true/false, "missing_info": ["<list of missing information>"], "contradictions": ["<list of contradictions>"], "reformulated_query": "<a better query to retrieve missing info, or null if sufficient>", "reasoning": "<brief explanation>"}}"""
