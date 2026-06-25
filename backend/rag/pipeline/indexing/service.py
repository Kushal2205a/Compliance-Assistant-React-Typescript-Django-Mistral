import json
import os

import numpy as np

from ..config import PipelineConfig
from ..embeddings.base import EmbeddingModel
from ..embeddings.models import SentenceTransformerModel
from ..ingestion import Document
from ..ingestion.parser import clean_document
from ..utils.hashing import file_hash
from .base import VectorStore
from .faiss_store import FaissVectorStore


class IndexResult:
    def __init__(
        self,
        chunks: list,
        vector_store: VectorStore,
        doc_hash: str,
    ):
        self.chunks = chunks
        self.vector_store = vector_store
        self.doc_hash = doc_hash

    def search(self, query_embedding: np.ndarray, k: int = 3):
        return self.vector_store.search(query_embedding, k)


class IndexManifest:
    def __init__(self, path: str):
        self.path = path
        self.data: dict = {"version": 1, "documents": {}}
        self._load()

    def has(self, doc_hash: str) -> bool:
        return doc_hash in self.data["documents"]

    def get_chunk_ids(self, doc_hash: str) -> list[str]:
        doc = self.data["documents"].get(doc_hash)
        return doc["chunk_ids"] if doc else []

    def add(self, doc_hash: str, doc_id: str, chunk_ids: list[str]) -> None:
        self.data["documents"][doc_hash] = {
            "doc_id": doc_id,
            "chunk_ids": chunk_ids,
        }
        self._save()

    def remove(self, doc_hash: str) -> list[str]:
        doc = self.data["documents"].pop(doc_hash, None)
        self._save()
        return doc["chunk_ids"] if doc else []

    def _load(self) -> None:
        if os.path.exists(self.path):
            with open(self.path) as f:
                self.data = json.load(f)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2)


class IndexingService:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.embedding_model: EmbeddingModel = SentenceTransformerModel(
            config.embedding.model_name, config.embedding.device
        )
        from ..chunking.service import ChunkingService

        self.chunker = ChunkingService(config.chunking)
        index_dir = config.indexing.index_dir
        os.makedirs(index_dir, exist_ok=True)
        self.faiss_path = os.path.join(index_dir, "index.faiss")
        self.manifest_path = os.path.join(index_dir, "manifest.json")
        self.manifest = IndexManifest(self.manifest_path)
        self.vector_store: VectorStore | None = None

    def _get_or_create_store(self) -> VectorStore:
        if self.vector_store is not None:
            return self.vector_store
        if os.path.exists(self.faiss_path):
            self.vector_store = FaissVectorStore.load(self.faiss_path)
        else:
            self.vector_store = FaissVectorStore(
                self.embedding_model.dimensions
            )
        return self.vector_store

    def index_document(
        self,
        file,
        document_id: str | None = None,
        progress_callback=None,
    ) -> IndexResult:
        def log(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        doc_hash = file_hash(file)
        store = self._get_or_create_store()

        if self.manifest.has(doc_hash):
            log("Loaded from cache.")
            chunk_ids = self.manifest.get_chunk_ids(doc_hash)
            cached_chunks = [
                c for c in store.chunks if c.id in chunk_ids
            ]
            if cached_chunks:
                return IndexResult(cached_chunks, store, doc_hash)

        log("Extracting text from PDF...")
        from ..ingestion.loader import load_pdf

        doc: Document = load_pdf(file)

        log("Cleaning document text...")
        doc.content = clean_document(doc.content)

        log("Chunking text...")
        doc_id = document_id or doc_hash[:12]
        chunks = self.chunker.chunk(doc.content, doc_id)
        log(f"Created {len(chunks)} chunks.")

        log("Generating embeddings...")
        texts = [c.content for c in chunks]
        embeddings = self.embedding_model.embed(texts)

        log("Adding to vector store...")
        store.add(chunks, embeddings)

        log("Saving index...")
        old_chunk_ids = self.manifest.get_chunk_ids(doc_hash)
        if old_chunk_ids:
            store.remove(old_chunk_ids)
        store.save(self.faiss_path)
        self.manifest.add(doc_hash, doc_id, [c.id for c in chunks])

        log("Indexing complete.")
        return IndexResult(chunks, store, doc_hash)

    def search(
        self,
        result: IndexResult,
        query: str,
        k: int = 3,
    ) -> list[tuple]:
        query_emb = self.embedding_model.embed_query(query)
        return result.search(query_emb, k)

    def get_chunk_texts(self, results: list[tuple]) -> list[str]:
        return [chunk.content for chunk, _ in results]
