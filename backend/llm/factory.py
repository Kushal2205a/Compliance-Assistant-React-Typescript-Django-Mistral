from .base import LLMProvider


def create_llm(model: str, base_url: str | None = None, api_key: str | None = None) -> LLMProvider:
    from .nvidia import NvidiaProvider

    return NvidiaProvider(model=model, base_url=base_url, api_key=api_key)
