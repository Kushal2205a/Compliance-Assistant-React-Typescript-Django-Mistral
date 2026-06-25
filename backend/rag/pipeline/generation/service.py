from llm.base import LLMProvider
from rag.pipeline.prompts import GENERATE_PROMPT


class GenerationService:
    def __init__(self, llm: LLMProvider | None = None):
        self._llm = llm

    def generate(
        self,
        query: str,
        context: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ) -> str:
        if not self._llm:
            return ""

        max_len = 3000
        if len(context) > max_len:
            context = context[:max_len].rsplit(" ", 1)[0]

        prompt = GENERATE_PROMPT.format(query=query, context=context)
        return self._llm.invoke(
            [
                {
                    "role": "system",
                    "content": "You are a compliance expert. Answer based ONLY on the provided context.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )

    def stream(
        self,
        query: str,
        context: str,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ):
        if not self._llm:
            return

        max_len = 3000
        if len(context) > max_len:
            context = context[:max_len].rsplit(" ", 1)[0]

        prompt = GENERATE_PROMPT.format(query=query, context=context)
        yield from self._llm.stream(
            [
                {
                    "role": "system",
                    "content": "You are a compliance expert. Answer based ONLY on the provided context.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
