import os
import uuid

from typing import BinaryIO

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.enums import ReviewStatus
from app.models.review import EvidenceDocument, Review
from app.services.review_service import ReviewService
from app.vectorstore.factory import get_vectorstore


class EvidenceService:
    def __init__(self, db: Session):
        self.db = db

    def _get_storage_path(self, review_id: uuid.UUID, filename: str) -> str:
        review_dir = os.path.join(settings.abs_storage_dir, str(review_id), "evidence")
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
        if not os.path.exists(doc.file_path):
            doc.status = "failed"
            self.db.commit()
            return doc

        from rag.pipeline.chunking.service import ChunkingService
        from rag.pipeline.config import ChunkingConfig
        from rag.pipeline.ingestion.loader import load_pdf
        from app.services.retrieval_service import _get_embedder

        chunk_config = ChunkingConfig(
            strategy=settings.chunk_strategy,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        chunker = ChunkingService(chunk_config)
        embedder = _get_embedder()

        with open(doc.file_path, "rb") as f:
            document, page_map = load_pdf(f, return_page_map=True)

        from rag.pipeline.ingestion.parser import clean_document
        document.content = clean_document(document.content)

        chunks = chunker.chunk(document.content, str(doc.id), page_map=page_map)

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

        vs.delete_by_document(str(doc.id))

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
                        "indexing_version": settings.indexing_version,
                        **chunk.metadata,
                    },
                )
            )

        vs.add(qdrant_chunks, embeddings)

        from app.services.bm25_index import get_bm25_index, reset_bm25_index
        reset_bm25_index()
        bm25 = get_bm25_index()
        bm25.build(qdrant_chunks)

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

    def update_review_status(self, review_id: uuid.UUID, target: ReviewStatus | None = None) -> None:
        docs = self.list_for_review(review_id)
        all_indexed = all(d.status == "indexed" for d in docs)
        if target:
            rsvc = ReviewService(self.db)
            rsvc.transition_status(review_id, target)
        elif all_indexed and docs:
            rsvc = ReviewService(self.db)
            rsvc.transition_status(review_id, ReviewStatus.READY)
