import json
import uuid
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.enums import JobStatus
from app.models.review import ControlEvaluation, Review, ReviewJob
from app.services.retrieval_service import RetrievalService


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
            yield json.dumps({"error": "Review not found"}) + "\n"
            return

        latest_job = (
            self.db.query(ReviewJob)
            .filter(
                ReviewJob.review_id == review_id,
                ReviewJob.status == JobStatus.COMPLETED.value,
            )
            .order_by(ReviewJob.created_at.desc())
            .first()
        )

        if not latest_job:
            yield json.dumps({
                "error": "chat_unavailable",
                "message": "Complete an evaluation before asking follow-up questions.",
            }) + "\n"
            return

        retrieval_svc = RetrievalService()
        query_emb = None

        from rag.pipeline.embeddings.models import SentenceTransformerModel
        embedder = SentenceTransformerModel(
            settings.embedding_model_name,
            settings.embedding_device,
        )
        query_emb = embedder.embed_query(question)

        vs = __import__("app.vectorstore.factory", fromlist=["get_vectorstore"])
        vs_store = vs.get_vectorstore()
        results = vs_store.search(query_emb, k=settings.retrieval_top_k)

        context_parts = []
        for r in results:
            ctx = r.chunk.metadata.get("filename", "Unknown")
            context_parts.append(f"[Source: {ctx}]\n{r.chunk.content}")

        context = "\n\n".join(context_parts) if context_parts else ""

        evaluations = (
            self.db.query(ControlEvaluation)
            .filter(ControlEvaluation.job_id == latest_job.id)
            .order_by(ControlEvaluation.processing_order)
            .all()
        )
        report_lines = []
        for ev in evaluations:
            report_lines.append(
                f"- [{ev.control_id}] {ev.control_name}: {ev.status} "
                f"(confidence: {ev.confidence:.2f})"
            )
        report_context = "\n".join(report_lines)

        from llm.factory import create_llm

        llm = create_llm(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.nvidia_api_key,
        )

        system_prompt = f"""You are a compliance audit assistant. Answer based on the evidence and evaluation results provided.

Review: {review.name}

Evaluation Summary (Job {latest_job.id}):
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
                yield json.dumps({"token": token}) + "\n"

        yield json.dumps({"done": True}) + "\n"
