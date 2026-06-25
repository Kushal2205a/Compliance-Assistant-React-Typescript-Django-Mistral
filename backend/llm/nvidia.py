import json
from typing import Any

import requests


class NvidiaProvider:
    def __init__(
        self,
        model: str = "nvidia/nemotron-3-super-120b-a12b",
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self._model = model
        if base_url:
            self._base_url = base_url.rstrip("/")
        else:
            self._base_url = "https://integrate.api.nvidia.com/v1"
        self._headers = {
            "Content-Type": "application/json",
        }
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    def _post(self, payload: dict) -> dict:
        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()

    def invoke(self, messages: list[dict], **kwargs: Any) -> str:
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }
        data = self._post(payload)
        return data["choices"][0]["message"]["content"]

    def stream(self, messages: list[dict], **kwargs: Any):
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 1024),
            "stream": True,
        }
        resp = requests.post(
            f"{self._base_url}/chat/completions",
            headers=self._headers,
            json=payload,
            stream=True,
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            if line.startswith(b"data: "):
                chunk = line[6:]
                if chunk.strip() == b"[DONE]":
                    break
                data = json.loads(chunk)
                delta = data["choices"][0].get("delta", {})
                yield delta.get("content", "")

    def invoke_tools(
        self, messages: list[dict], tools: list[dict], **kwargs: Any
    ) -> dict:
        payload = {
            "model": self._model,
            "messages": messages,
            "tools": tools,
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("max_tokens", 1024),
        }
        data = self._post(payload)
        message = data["choices"][0]["message"]
        return {
            "content": message.get("content", ""),
            "tool_calls": [
                {
                    "function": {
                        "name": tc["function"]["name"],
                        "arguments": tc["function"].get("arguments", "{}"),
                    }
                }
                for tc in message.get("tool_calls", [])
            ],
        }

    @property
    def model_name(self) -> str:
        return self._model
