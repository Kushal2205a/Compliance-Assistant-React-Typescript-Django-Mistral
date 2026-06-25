import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config.settings import settings
from .base import ChunkData, SearchResult, VectorStore


class QdrantVectorStore(VectorStore):
    def __init__(self, url: str | None = None, collection: str | None = None):
        self._client = QdrantClient(url=url or settings.qdrant_url)
        self._collection = collection or settings.qdrant_collection
        self._dimension: int | None = None

    def _ensure_collection(self, dimension: int) -> None:
        if self._dimension is not None:
            return
        self._dimension = dimension
        collections = self._client.get_collections().collections
        names = [c.name for c in collections]
        if self._collection not in names:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qmodels.VectorParams(
                    size=dimension,
                    distance=qmodels.Distance.COSINE,
                ),
            )

    def add(self, chunks: list[ChunkData], embeddings: np.ndarray) -> None:
        if not chunks or embeddings.shape[0] == 0:
            return
        self._ensure_collection(embeddings.shape[1])

        points = []
        for chunk, embedding in zip(chunks, embeddings):
            points.append(
                qmodels.PointStruct(
                    id=chunk.id,
                    vector=embedding.tolist(),
                    payload={
                        "document_id": chunk.document_id,
                        "content": chunk.content,
                        **chunk.metadata,
                    },
                )
            )
        self._client.upsert(collection_name=self._collection, points=points)

    def search(self, query_embedding: np.ndarray, k: int) -> list[SearchResult]:
        if self._dimension is None:
            return []
        hits = self._client.search(
            collection_name=self._collection,
            query_vector=query_embedding.tolist(),
            limit=k,
        )
        results = []
        for hit in hits:
            payload = hit.payload or {}
            chunk = ChunkData(
                id=hit.id,
                document_id=payload.get("document_id", ""),
                content=payload.get("content", ""),
                metadata={k: v for k, v in payload.items() if k not in ("document_id", "content")},
            )
            results.append(SearchResult(chunk=chunk, score=hit.score))
        return results

    def get_chunks_by_ids(self, chunk_ids: list[str]) -> list[ChunkData]:
        if not chunk_ids:
            return []
        try:
            points = self._client.retrieve(
                collection_name=self._collection,
                ids=chunk_ids,
            )
        except Exception:
            return []
        chunks = []
        for point in points:
            payload = point.payload or {}
            chunks.append(
                ChunkData(
                    id=point.id,
                    document_id=payload.get("document_id", ""),
                    content=payload.get("content", ""),
                    metadata={k: v for k, v in payload.items() if k not in ("document_id", "content")},
                )
            )
        return chunks

    def delete(self, chunk_ids: list[str]) -> None:
        if not chunk_ids:
            return
        self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.PointIdsList(points=chunk_ids),
        )

    def delete_by_document(self, document_id: str) -> None:
        self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="document_id",
                            match=qmodels.MatchValue(value=document_id),
                        )
                    ]
                )
            ),
        )

    def count(self) -> int:
        result = self._client.count(collection_name=self._collection)
        return result.count

    def clear(self) -> None:
        self._client.delete_collection(collection_name=self._collection)
        self._dimension = None
