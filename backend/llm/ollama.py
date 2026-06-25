from typing import Any

import ollama


class OllamaProvider:
    def __init__(self, model: str = "mistral", base_url: str | None = None):
        self._model = model
        self._client_kwargs = {}
        if base_url:
            self._client_kwargs["host"] = base_url

    def invoke(self, messages: list[dict], **kwargs: Any) -> str:
        response = ollama.chat(
            model=self._model,
            messages=messages,
            options={"temperature": kwargs.get("temperature", 0.0)},
            **self._client_kwargs,
        )
        return response["message"]["content"]

    def stream(self, messages: list[dict], **kwargs: Any):
        stream = ollama.chat(
            model=self._model,
            messages=messages,
            stream=True,
            options={"temperature": kwargs.get("temperature", 0.0)},
            **self._client_kwargs,
        )
        for chunk in stream:
            yield chunk["message"]["content"]

    def invoke_tools(
        self, messages: list[dict], tools: list[dict], **kwargs: Any
    ) -> dict:
        response = ollama.chat(
            model=self._model,
            messages=messages,
            tools=tools,
            options={"temperature": kwargs.get("temperature", 0.0)},
            **self._client_kwargs,
        )
        return response["message"]

    @property
    def model_name(self) -> str:
        return self._model
