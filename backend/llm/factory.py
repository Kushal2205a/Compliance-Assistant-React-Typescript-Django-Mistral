from .base import LLMProvider


def create_llm(provider: str, model: str, base_url: str | None = None, api_key: str | None = None) -> LLMProvider:
    if provider == "ollama":
        from .ollama import OllamaProvider

        return OllamaProvider(model=model, base_url=base_url)
    elif provider == "nvidia":
        from .nvidia import NvidiaProvider

        return NvidiaProvider(model=model, base_url=base_url, api_key=api_key)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")
