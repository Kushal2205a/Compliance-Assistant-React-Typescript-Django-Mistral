import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.session import SessionLocal
from app.models.enums import EventType, JobStatus
from app.models.review import ControlEvaluation, ReviewJob
from app.services.adaptive_retrieval import get_adaptive_retrieval_service
from app.services.checklist_service import ChecklistService
from app.services.compliance_evaluation_service import ComplianceEvaluationService
from app.services.event_bus import get_event_bus
from app.services.evidence_formatter import format_evidence
from app.services.grounding_check import check_grounding
from app.services.retrieval_service import RetrievalResult, RetrievalService
from app.vectorstore.factory import get_vectorstore

_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_MAIN_LOOP: asyncio.AbstractEventLoop | None = None


def _publish_sync(bus, job_id, event_type, **data):
    """Publish an event from a synchronous worker thread."""
    loop = _MAIN_LOOP
    if loop is None:
        return
    fut = asyncio.run_coroutine_threadsafe(
        bus.publish(job_id, event_type, **data),
        loop,
    )
    fut.result(timeout=10)


async def run_evaluation_worker(job_id: uuid.UUID) -> None:
    global _MAIN_LOOP
    _MAIN_LOOP = asyncio.get_event_loop()
    print(f"[worker] spawning worker thread for job {job_id}")
    await _MAIN_LOOP.run_in_executor(_EXECUTOR, _run_worker_sync, job_id)


def _run_worker_sync(job_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        bus = get_event_bus()
        retrieval_svc = RetrievalService()
        eval_svc = ComplianceEvaluationService()
        cl_svc = ChecklistService(db)

        job = db.query(ReviewJob).filter(ReviewJob.id == job_id).first()
        if not job:
            print(f"[worker] Job {job_id} not found, aborting")
            return

        job.status = JobStatus.RUNNING.value
        db.commit()
        print(f"[worker] Job {job_id} started")

        checklist = job.checklist
        if not checklist:
            raise ValueError(f"No checklist found for job {job_id}")

        controls = cl_svc.parse_checklist(checklist.file_path)
        job.total_controls = len(controls)
        db.commit()
        print(f"[worker] Parsed {len(controls)} controls from checklist")

        eval_start = time.time()
        total_confidence = 0.0
        implemented_count = 0
        partial_count = 0

        for idx, control in enumerate(controls):
            t_control_start = time.time()
            control_id = f"C{idx + 1:03d}"
            print(f"\n{'='*60}")
            print(f"[worker] Control {idx+1}/{len(controls)}: {control_id} - {control.name[:60]}")
            print(f"{'='*60}")

            _publish_sync(bus, 
                str(job.id),
                EventType.CONTROL_STARTED,
                review_id=str(job.review_id),
                control_id=control_id,
                control_name=control.name,
                control_description=control.description or "",
                progress=idx,
                total=len(controls),
            )

            query = control.name
            print(f"[worker] Query: {query[:80]}")

            _publish_sync(bus, 
                str(job.id),
                EventType.RETRIEVAL_STARTED,
                review_id=str(job.review_id),
                control_id=control_id,
                query=query,
            )

            # --- Adaptive retrieval with full metadata ---
            retrieval_attempts = 1
            rewritten_query = None
            retrieval_diagnostics = None

            if settings.adaptive_retrieval_enabled:
                print(f"[worker]  → adaptive retrieval...")
                adaptive = get_adaptive_retrieval_service()
                result = adaptive.retrieve_with_adaptive(
                    query,
                    retrieval_svc.retrieve,
                    top_k=settings.retrieval_top_k,
                )
                retrieval_attempts = result.attempts
                rewritten_query = result.rewritten_queries[-1] if result.rewritten_queries else None
                retrieval_result = RetrievalResult(
                    chunks=result.chunks,
                    evidence_refs=result.evidence_refs,
                    diagnostics=result.diagnostics,
                )
            else:
                print(f"[worker]  → direct retrieval...")
                retrieval_result = retrieval_svc.retrieve(query)

            retrieval_diagnostics = retrieval_result.diagnostics
            print(f"[worker]  ← found {len(retrieval_result.evidence_refs)} evidence refs (attempts={retrieval_attempts})")

            _publish_sync(bus, 
                str(job.id),
                EventType.RETRIEVAL_COMPLETED,
                review_id=str(job.review_id),
                control_id=control_id,
                chunks_found=len(retrieval_result.evidence_refs),
                diagnostics=retrieval_diagnostics.to_dict() if retrieval_diagnostics else {},
            )

            _publish_sync(bus, 
                str(job.id),
                EventType.EVALUATION_STARTED,
                review_id=str(job.review_id),
                control_id=control_id,
            )

            # --- Format evidence before sending to evaluator ---
            t_format_start = time.time()
            formatted_evidence = format_evidence(retrieval_result.evidence_refs)
            t_format_end = time.time()
            print(f"[worker]  → formatted {len(formatted_evidence)} evidence blocks ({t_format_end - t_format_start:.1f}s)")

            t_eval_start = time.time()
            print(f"[worker]  → calling LLM ({settings.llm_model})...")
            eval_result = eval_svc.evaluate(
                control.name,
                control.description,
                formatted_evidence,
            )
            t_eval_end = time.time()
            eval_secs = t_eval_end - t_eval_start
            print(f"[worker]  ← LLM done ({eval_secs:.1f}s): status={eval_result.status}, confidence={eval_result.confidence:.2f}")

            if retrieval_diagnostics:
                retrieval_diagnostics.llm_ms = eval_secs * 1000
                retrieval_diagnostics.format_ms = (t_format_end - t_format_start) * 1000

            evidence_texts = [fe.text for fe in formatted_evidence if fe.text]
            grounded_status, grounded_confidence, grounding_warnings = check_grounding(
                eval_result.explanation,
                evidence_texts,
                eval_result.status,
                eval_result.confidence,
            )
            if grounded_status != eval_result.status or grounded_confidence != eval_result.confidence:
                print(f"[worker]  → grounding adjusted: {eval_result.status}/{eval_result.confidence:.2f} → {grounded_status}/{grounded_confidence:.2f}")
                if grounding_warnings:
                    print(f"[worker]  → grounding warning: {grounding_warnings[:200]}")
            eval_result.status = grounded_status
            eval_result.confidence = grounded_confidence
            if grounding_warnings:
                eval_result.explanation += f"\n\n**Grounding Warning:** {grounding_warnings}"

            _publish_sync(bus, 
                str(job.id),
                EventType.EVALUATION_COMPLETED,
                review_id=str(job.review_id),
                control_id=control_id,
                status=eval_result.status,
                confidence=eval_result.confidence,
            )

            evidence_dicts = [fe.to_dict() for fe in formatted_evidence]
            t_control_end = time.time()
            control_timing = (t_control_end - t_control_start) * 1000

            control_eval = ControlEvaluation(
                id=uuid.uuid4(),
                review_id=job.review_id,
                job_id=job.id,
                control_id=control_id,
                control_name=control.name,
                control_description=control.description or "",
                status=eval_result.status,
                confidence=eval_result.confidence,
                explanation=eval_result.explanation,
                recommendation=eval_result.recommendation,
                supporting_evidence=json.dumps(evidence_dicts),
                processing_order=idx,
                original_query=query,
                rewritten_query=rewritten_query,
                retrieval_attempts=retrieval_attempts,
                retrieval_metadata=json.dumps(retrieval_diagnostics.to_dict() if retrieval_diagnostics else {}),
                control_timing_ms=round(control_timing, 1),
            )
            db.add(control_eval)
            db.commit()

            total_confidence += eval_result.confidence
            if eval_result.status == "implemented":
                implemented_count += 1
            elif eval_result.status == "partially_implemented":
                partial_count += 1

            job.evaluated_controls = idx + 1
            db.commit()

            _publish_sync(bus, 
                str(job.id),
                EventType.CONTROL_COMPLETED,
                review_id=str(job.review_id),
                control_id=control_id,
                control_name=control.name,
                control_description=control.description or "",
                status=eval_result.status,
                confidence=eval_result.confidence,
                explanation=eval_result.explanation,
                recommendation=eval_result.recommendation,
                evidence=evidence_dicts,
                retrieval_metadata=retrieval_diagnostics.to_dict() if retrieval_diagnostics else {},
                original_query=query,
                rewritten_query=rewritten_query,
                retrieval_attempts=retrieval_attempts,
                progress=idx + 1,
                total=len(controls),
            )

        elapsed = time.time() - eval_start
        avg_conf = total_confidence / len(controls) if controls else 0.0
        overall_pct = ((implemented_count + 0.5 * partial_count) / len(controls) * 100) if controls else 0.0

        job.status = JobStatus.COMPLETED.value
        job.overall_percentage = round(overall_pct, 1)
        job.average_confidence = round(avg_conf, 2)
        job.processing_time = round(elapsed, 2)
        job.completed_at = datetime.utcnow()

        review = job.review
        if review:
            review.status = "completed"
        db.commit()

        print(f"\n{'='*60}")
        print(f"[worker] JOB COMPLETE: {elapsed:.1f}s total")
        print(f"[worker] Score: {job.overall_percentage}% | Confidence: {job.average_confidence:.2f}")
        print(f"[worker] Implemented: {implemented_count}/{len(controls)} | Partial: {partial_count}/{len(controls)}")
        print(f"{'='*60}\n")

        _publish_sync(bus, 
            str(job.id),
            EventType.JOB_COMPLETED,
            review_id=str(job.review_id),
            total_controls=len(controls),
            evaluated_controls=len(controls),
            overall_percentage=round(overall_pct, 1),
            average_confidence=round(avg_conf, 2),
            processing_time=round(elapsed, 2),
        )

    except Exception as e:
        print(f"[worker] ERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        try:
            job = db.query(ReviewJob).filter(ReviewJob.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED.value
                job.error_message = str(e)
                review = job.review
                if review:
                    review.status = "failed"
                db.commit()
        except Exception:
            pass

        bus = get_event_bus()
        _publish_sync(bus, 
            str(job_id),
            EventType.JOB_FAILED,
            error=str(e),
        )

    finally:
        db.close()
