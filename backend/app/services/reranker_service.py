import os
import torch
from abc import ABC, abstractmethod

from app.config.settings import settings


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, texts: list[str], top_k: int) -> list[tuple[str, float]]:
        pass


class CrossEncoderReranker(Reranker):
    def __init__(self, model_name: str | None = None):
        self._model = None
        self._tokenizer = None
        self._model_name = model_name or settings.reranker_model

    def _load(self):
        if self._model is not None:
            return
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        print(f"[reranker] loading {self._model_name}...", flush=True)
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_name)
        print(f"[reranker] tokenizer loaded", flush=True)
        self._model = AutoModelForSequenceClassification.from_pretrained(
            self._model_name
        )
        self._model.eval()
        print(f"[reranker] model loaded", flush=True)

    def rerank(self, query: str, texts: list[str], top_k: int) -> list[tuple[str, float]]:
        if not texts:
            return []
        if not settings.reranker_enabled:
            return [(text, 1.0) for text in texts[:top_k]]

        if self._model is None:
            print(f"[reranker] model not loaded, skipping", flush=True)
            return [(text, 1.0) for text in texts[:top_k]]

        pairs = [(query, text) for text in texts]
        inputs = self._tokenizer(
            pairs,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=512,
        )
        with torch.no_grad():
            outputs = self._model(**inputs)
            scores = outputs.logits.squeeze(-1).tolist()
        if isinstance(scores, float):
            scores = [scores]
        scored = list(zip(texts, scores))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


_reranker_instance: Reranker | None = None


def get_reranker() -> Reranker:
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = CrossEncoderReranker()
    return _reranker_instance
