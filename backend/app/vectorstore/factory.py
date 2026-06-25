import logging

from .base import VectorStore
from .qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)

_vector_store: VectorStore | None = None


def create_vectorstore() -> VectorStore:
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    try:
        store = QdrantVectorStore()
        store.count()
        _vector_store = store
        logger.info("Using Qdrant vector store")
    except Exception as e:
        logger.warning("Qdrant unavailable (%s), using in-memory store", e)
        from .memory import InMemoryVectorStore
        _vector_store = InMemoryVectorStore()

    return _vector_store


def get_vectorstore() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        return create_vectorstore()
    return _vector_store
