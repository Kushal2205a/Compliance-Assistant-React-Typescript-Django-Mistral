import json
import time
import uuid
from collections.abc import Generator

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.review import ControlEvaluation, EvidenceDocument, Review
from app.services.checklist_service import ParsedControl
from app.services.review_service import ReviewService
from app.vectorstore.factory import create_vectorstore


class EvaluationService:
    def __init__(self, db: Session):
        self.db = db

    def evaluate_controls(
        self,
        review_id: uuid.UUID,
        controls: list[ParsedControl],
    ) -> Generator[str, None, None]:
        review_service = ReviewService(self.db)
        review_service.update_status(review_id, "evaluating")

        review_service.update_summary(
            review_id,
            total_controls=len(controls),
            evaluated_controls=0,
        )

        start_time = time.time()
        total_confidence = 0.0
        implemented_count = 0

        for idx, control in enumerate(controls):
            control_id = uuid.uuid4()

            yield json.dumps({
                "type": "progress",
                "control_id": control.control_id,
                "control_name": control.name,
                "status": "searching",
                "progress": idx,
                "total": len(controls),
            }) + "\n"

            search_result = self._search_evidence(control)

            yield json.dumps({
                "type": "progress",
                "control_id": control.control_id,
                "control_name": control.name,
                "status": "evaluating",
                "progress": idx,
                "total": len(controls),
                "chunks_found": len(search_result["chunks"]),
            }) + "\n"

            eval_result = self._evaluate_control(control, search_result["chunks"])

            control_eval = ControlEvaluation(
                id=control_id,
                review_id=review_id,
                control_id=control.control_id,
                control_name=control.name,
                control_description=control.description,
                status=eval_result["status"],
                confidence=eval_result["confidence"],
                explanation=eval_result["explanation"],
                recommendation=eval_result.get("recommendation", ""),
                supporting_evidence=json.dumps(search_result["evidence_refs"]),
                processing_order=idx,
            )
            self.db.add(control_eval)
            self.db.commit()

            review_service.update_summary(
                review_id,
                evaluated_controls=idx + 1,
            )

            total_confidence += eval_result["confidence"]
            if eval_result["status"] in ("implemented", "partially_implemented"):
                implemented_count += 1

            yield json.dumps({
                "type": "result",
                "control_id": control.control_id,
                "control_name": control.name,
                "status": eval_result["status"],
                "confidence": eval_result["confidence"],
                "explanation": eval_result["explanation"],
                "recommendation": eval_result.get("recommendation", ""),
                "evidence": search_result["evidence_refs"],
                "progress": idx + 1,
                "total": len(controls),
            }) + "\n"

        elapsed = time.time() - start_time
        avg_conf = total_confidence / len(controls) if controls else 0.0
        overall_pct = (implemented_count / len(controls) * 100) if controls else 0.0

        review_service.update_summary(
            review_id,
            evaluated_controls=len(controls),
            overall_percentage=round(overall_pct, 1),
            average_confidence=round(avg_conf, 2),
            processing_time=round(elapsed, 2),
        )
        review_service.update_status(review_id, "completed")

        yield json.dumps({
            "type": "completed",
            "total_controls": len(controls),
            "overall_percentage": round(overall_pct, 1),
            "average_confidence": round(avg_conf, 2),
            "processing_time": round(elapsed, 2),
        }) + "\n"

    def _search_evidence(self, control: ParsedControl) -> dict:
        from rag.pipeline.embeddings.models import SentenceTransformerModel

        embedder = SentenceTransformerModel(
            settings.embedding_model_name,
            settings.embedding_device,
        )

        query = f"{control.name}: {control.description}" if control.description else control.name
        query_emb = embedder.embed_query(query)

        vs = create_vectorstore()

        results = vs.search(query_emb, k=settings.retrieval_top_k)

        chunks = []
        evidence_refs = []
        for r in results:
            chunks.append(r.chunk)
            evidence_refs.append({
                "doc_id": r.chunk.document_id,
                "content": r.chunk.content[:300],
                "score": round(r.score, 3),
                "metadata": r.chunk.metadata,
            })

        return {"chunks": chunks, "evidence_refs": evidence_refs}

    def _evaluate_control(self, control: ParsedControl, chunks: list) -> dict:
        from llm.factory import create_llm

        llm = create_llm(
            model=settings.llm_model,
            base_url=settings.llm_base_url,
            api_key=settings.nvidia_api_key,
        )

        context = "\n\n".join(c.content[:1000] for c in chunks[:5]) if chunks else "No evidence found."

        prompt = f"""You are evaluating whether company evidence supports a compliance control.

Control: {control.name}
Control Description: {control.description}

Evidence:
{context}

Evaluate if the evidence supports this control. Respond with a JSON object:
{{
    "status": "implemented" or "partially_implemented" or "missing" or "insufficient_evidence",
    "confidence": <0.0-1.0>,
    "explanation": "<why this status was assigned>",
    "recommendation": "<what evidence would improve this, or empty string if sufficient>"
}}

Rules:
- "implemented": clear evidence directly supports the control
- "partially_implemented": some evidence exists but gaps remain
- "missing": no relevant evidence found
- "insufficient_evidence": evidence exists but is too vague or indirect
- Confidence should reflect how certain you are (0.0-1.0)
- Be conservative: prefer slightly lower confidence when unsure"""

        response = llm.invoke([
            {"role": "system", "content": "You are a SOC2 compliance auditor evaluating evidence. Return ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ])

        import re
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                valid_statuses = ("implemented", "partially_implemented", "missing", "insufficient_evidence")
                if result.get("status") not in valid_statuses:
                    result["status"] = "insufficient_evidence"
                return result
            except json.JSONDecodeError:
                pass

        if not chunks:
            return {
                "status": "missing",
                "confidence": 0.0,
                "explanation": "No supporting evidence found for this control.",
                "recommendation": "Upload documentation addressing this control.",
            }

        return {
            "status": "insufficient_evidence",
            "confidence": 0.3,
            "explanation": "Could not determine compliance status from the available evidence.",
            "recommendation": "Review the control and upload additional documentation.",
        }
