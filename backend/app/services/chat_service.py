import json as json
import uuid
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.review import ControlEvaluation, Review
from app.vectorstore.factory import create_vectorstore
from app.vectorstore.base import ChunkData


class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def ask(
        self,
        review_id: uuid.UUID,
        question: str,
    ) -> Generator[str, None, None]:
        review = self.db.query(Review).filter(Review.id == review_id).first()
        if not review:
            yield '{"error": "Review not found"}\n'
            return

        from rag.pipeline.embeddings.models import SentenceTransformerModel

        embedder = SentenceTransformerModel(
            settings.embedding_model_name,
            settings.embedding_device,
        )
        query_emb = embedder.embed_query(question)

        vs = create_vectorstore()
        results = vs.search(query_emb, k=settings.retrieval_top_k)

        context_parts = []
        for r in results:
            ctx = r.chunk.metadata.get("filename", "Unknown")
            context_parts.append(f"[Source: {ctx}]\n{r.chunk.content}")

        context = "\n\n".join(context_parts) if context_parts else ""

        report_context = ""
        evaluations = (
            self.db.query(ControlEvaluation)
            .filter(ControlEvaluation.review_id == review_id)
            .order_by(ControlEvaluation.processing_order)
            .all()
        )
        if evaluations:
            report_lines = []
            for ev in evaluations:
                report_lines.append(f"- {ev.control_name}: {ev.status} (confidence: {ev.confidence:.2f})")
            report_context = "\n".join(report_lines)

        from llm.factory import create_llm

        llm = create_llm(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.nvidia_api_key,
        )

        system_prompt = f"""You are a compliance audit assistant. Answer based on the evidence and evaluation results provided.

Review: {review.name}

Evaluation Summary:
{report_context}

Relevant Evidence:
{context}

Answer the user's question based on the evidence and evaluation results above."""

        for token in llm.stream(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            temperature=0.0,
            max_tokens=settings.generation_max_tokens,
        ):
            if token:
                yield f'{{"token": {json.dumps(token)}}}\n'

        yield '{"done": true}\n'
