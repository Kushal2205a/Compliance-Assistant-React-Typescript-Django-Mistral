import numpy as np
from sentence_transformers import SentenceTransformer

from .base import EmbeddingModel


class SentenceTransformerModel(EmbeddingModel):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = "cpu"):
        self._model = SentenceTransformer(model_name, device=device)
        self._dim = getattr(self._model, 'get_embedding_dimension', self._model.get_sentence_embedding_dimension)()

    def embed(self, texts: list[str]) -> np.ndarray:
        embeddings = self._model.encode(texts, show_progress_bar=False)
        return np.array(embeddings, dtype="float32")

    def embed_query(self, text: str) -> np.ndarray:
        embedding = self._model.encode(text, show_progress_bar=False)
        return np.array(embedding, dtype="float32").flatten()

    @property
    def dimensions(self) -> int:
        return self._dim
