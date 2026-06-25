REWRITE_PROMPT = """Rewrite the following query to improve retrieval accuracy.

Rules:
- Keep the original meaning intact
- Use precise terminology relevant to compliance and security documents
- Expand acronyms where appropriate
- Remove ambiguous phrasing

Original query: {query}

Return ONLY the rewritten query, no explanation."""
