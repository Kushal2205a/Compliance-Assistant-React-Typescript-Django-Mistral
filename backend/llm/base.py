from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    @abstractmethod
    def invoke(self, messages: list[dict], **kwargs: Any) -> str:
        pass

    @abstractmethod
    def stream(self, messages: list[dict], **kwargs: Any):
        pass

    @abstractmethod
    def invoke_tools(
        self, messages: list[dict], tools: list[dict], **kwargs: Any
    ) -> dict:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass
