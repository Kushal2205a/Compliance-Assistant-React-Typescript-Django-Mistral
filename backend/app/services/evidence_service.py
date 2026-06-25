import os
import uuid
from datetime import datetime
from typing import BinaryIO

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.review import EvidenceDocument, Review
from app.vectorstore.factory import get_vectorstore


class EvidenceService:
    def __init__(self, db: Session):
        self.db = db

    def _get_storage_path(self, review_id: uuid.UUID, filename: str) -> str:
        review_dir = os.path.join(settings.storage_dir, str(review_id), "evidence")
        os.makedirs(review_dir, exist_ok=True)
        return os.path.join(review_dir, filename)

    def upload(
        self,
        review_id: uuid.UUID,
        filename: str,
        file: BinaryIO,
    ) -> EvidenceDocument:
        doc_id = uuid.uuid4()
        file_path = self._get_storage_path(review_id, f"{doc_id}_{filename}")

        with open(file_path, "wb") as f:
            f.write(file.read())

        doc = EvidenceDocument(
            id=doc_id,
            review_id=review_id,
            filename=filename,
            file_path=file_path,
            status="uploaded",
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def index_document(self, doc: EvidenceDocument) -> EvidenceDocument:
        from rag.pipeline.chunking.service import ChunkingService
        from rag.pipeline.config import ChunkingConfig
        from rag.pipeline.embeddings.models import SentenceTransformerModel
        from rag.pipeline.ingestion.loader import load_pdf

        chunk_config = ChunkingConfig(
            strategy=settings.chunk_strategy,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunker = ChunkingService(chunk_config)
        embedder = SentenceTransformerModel(
            settings.embedding_model_name,
            settings.embedding_device,
        )

        with open(doc.file_path, "rb") as f:
            document = load_pdf(f)

        from rag.pipeline.ingestion.parser import clean_document
        document.content = clean_document(document.content)

        chunks = chunker.chunk(document.content, str(doc.id))

        if not chunks:
            doc.status = "indexed"
            doc.chunk_count = 0
            self.db.commit()
            self.db.refresh(doc)
            return doc

        texts = [c.content for c in chunks]
        embeddings = embedder.embed(texts)

        vs = get_vectorstore()
        from app.vectorstore.base import ChunkData

        qdrant_chunks = []
        for chunk in chunks:
            qdrant_chunks.append(
                ChunkData(
                    id=chunk.id,
                    document_id=str(doc.id),
                    content=chunk.content,
                    metadata={
                        "review_id": str(doc.review_id),
                        "filename": doc.filename,
                        **chunk.metadata,
                    },
                )
            )

        vs.add(qdrant_chunks, embeddings)

        doc.status = "indexed"
        doc.chunk_count = len(chunks)
        doc.doc_hash = ""
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def list_for_review(self, review_id: uuid.UUID) -> list[EvidenceDocument]:
        return (
            self.db.query(EvidenceDocument)
            .filter(EvidenceDocument.review_id == review_id)
            .order_by(EvidenceDocument.created_at.desc())
            .all()
        )

    def delete(self, doc_id: uuid.UUID) -> bool:
        doc = self.db.query(EvidenceDocument).filter(EvidenceDocument.id == doc_id).first()
        if not doc:
            return False
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)
        self.db.delete(doc)
        self.db.commit()
        return True

    def update_review_status(self, review_id: uuid.UUID) -> None:
        docs = self.list_for_review(review_id)
        all_indexed = all(d.status == "indexed" for d in docs)
        if all_indexed and docs:
            review_svc = __import__("app.services.review_service", fromlist=["ReviewService"])
            rsvc = review_svc.ReviewService(self.db)
            rsvc.update_status(review_id, "ready")
