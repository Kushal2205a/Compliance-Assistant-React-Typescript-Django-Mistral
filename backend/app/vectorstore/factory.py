from .base import VectorStore
from .qdrant import QdrantVectorStore


def create_vectorstore() -> VectorStore:
    return QdrantVectorStore()
