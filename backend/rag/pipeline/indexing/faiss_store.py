import json
import os

import faiss
import numpy as np

from ..chunking import Chunk
from .base import VectorStore


class FaissVectorStore(VectorStore):
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.chunks: list[Chunk] = []
        self.id_map: dict[str, int] = {}

    def add(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        if len(chunks) == 0:
            return
        if embeddings.shape[0] != len(chunks):
            raise ValueError("Embedding count must match chunk count")
        embeddings = embeddings.astype("float32")
        if embeddings.ndim == 1:
            embeddings = embeddings.reshape(1, -1)
        faiss.normalize_L2(embeddings)
        start = self.index.ntotal
        self.index.add(embeddings)
        for i, chunk in enumerate(chunks):
            self.chunks.append(chunk)
            self.id_map[chunk.id] = start + i

    def search(
        self, query_embedding: np.ndarray, k: int
    ) -> list[tuple[Chunk, float]]:
        query_embedding = query_embedding.astype("float32").reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        distances, indices = self.index.search(query_embedding, k)
        results: list[tuple[Chunk, float]] = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            results.append((self.chunks[idx], float(dist)))
        return results

    def remove(self, chunk_ids: list[str]) -> None:
        ids_to_remove = [self.id_map[cid] for cid in chunk_ids if cid in self.id_map]
        if not ids_to_remove:
            return
        keep_mask = np.ones(self.index.ntotal, dtype=bool)
        for idx in ids_to_remove:
            keep_mask[idx] = False
        kept_embeddings = self.index.reconstruct_n(0, self.index.ntotal)[keep_mask]
        self.index.reset()
        if kept_embeddings.shape[0] > 0:
            if kept_embeddings.ndim == 1:
                kept_embeddings = kept_embeddings.reshape(1, -1)
            faiss.normalize_L2(kept_embeddings)
            self.index.add(kept_embeddings)
        self.chunks = [c for i, c in enumerate(self.chunks) if keep_mask[i]]
        self.id_map = {c.id: i for i, c in enumerate(self.chunks)}

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        faiss.write_index(self.index, path)
        meta_path = path + ".meta.json"
        with open(meta_path, "w") as f:
            json.dump(
                {
                    "dimension": self.dimension,
                    "chunks": [
                        {
                            "id": c.id,
                            "document_id": c.document_id,
                            "content": c.content,
                            "metadata": c.metadata,
                        }
                        for c in self.chunks
                    ],
                },
                f,
            )

    @classmethod
    def load(cls, path: str, chunks: list[Chunk] | None = None) -> "FaissVectorStore":
        index = faiss.read_index(path)
        dimension = index.d
        store = cls(dimension)
        store.index = index
        meta_path = path + ".meta.json"
        if os.path.exists(meta_path) and chunks is None:
            with open(meta_path) as f:
                data = json.load(f)
            for cdata in data["chunks"]:
                chunk = Chunk(
                    id=cdata["id"],
                    document_id=cdata["document_id"],
                    content=cdata["content"],
                    metadata=cdata["metadata"],
                )
                store.chunks.append(chunk)
                store.id_map[chunk.id] = len(store.chunks) - 1
        elif chunks is not None:
            store.chunks = list(chunks)
            store.id_map = {c.id: i for i, c in enumerate(chunks)}
        return store

    def clear(self) -> None:
        self.index.reset()
        self.chunks.clear()
        self.id_map.clear()
