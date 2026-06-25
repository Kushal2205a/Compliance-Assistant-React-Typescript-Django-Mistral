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
from app.services.control_grouper import ControlGroup, get_control_grouper
from app.services.event_bus import get_event_bus
from app.services.evidence_formatter import format_evidence
from app.services.grounding_check import check_grounding
from app.services.retrieval_service import RetrievalResult, RetrievalService

_EXECUTOR = ThreadPoolExecutor(max_workers=1)
_MAIN_LOOP: asyncio.AbstractEventLoop | None = None


def _publish_sync(bus, job_id, event_type, **data):
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


def _retrieve_for_group(
    group: ControlGroup,
    retrieval_svc: RetrievalService,
    bus,
    job,
) -> tuple:
    """Retrieve evidence for a control group. Returns (RetrievalResult, formatted_evidence)."""
    query = group.query
    print(f"[worker]  → retrieval query: {query[:100]}...")

    retrieval_attempts = 1
    rewritten_query = None

    _publish_sync(
        bus,
        str(job.id),
        EventType.RETRIEVAL_STARTED,
        review_id=str(job.review_id),
        control_id=group.controls[0].control_id,
        query=query,
    )

    if settings.adaptive_retrieval_enabled:
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
        retrieval_result = retrieval_svc.retrieve(query)

    print(f"[worker]  ← found {len(retrieval_result.evidence_refs)} evidence refs (attempts={retrieval_attempts})")

    _publish_sync(
        bus,
        str(job.id),
        EventType.RETRIEVAL_COMPLETED,
        review_id=str(job.review_id),
        control_id=group.controls[0].control_id,
        chunks_found=len(retrieval_result.evidence_refs),
        diagnostics=retrieval_result.diagnostics.to_dict() if retrieval_result.diagnostics else {},
    )

    t_format_start = time.time()
    formatted_evidence = format_evidence(retrieval_result.evidence_refs)
    t_format_end = time.time()
    print(f"[worker]  → formatted {len(formatted_evidence)} evidence blocks ({t_format_end - t_format_start:.1f}s)")

    if retrieval_result.diagnostics:
        retrieval_result.diagnostics.format_ms = (t_format_end - t_format_start) * 1000

    return retrieval_result, formatted_evidence, retrieval_attempts, rewritten_query


def _evaluate_group(
    group: ControlGroup,
    eval_svc: ComplianceEvaluationService,
    formatted_evidence: list,
    retrieval_diagnostics,
    retrieval_attempts: int,
    rewritten_query: str | None,
    bus,
    job,
    db,
    global_idx: int,
    total_controls: int,
    stats: dict,
) -> int:
    """Evaluate all controls in a group. Returns next global_idx."""
    batch_limit = settings.batch_size
    is_batch_mode = settings.evaluation_mode != "individual"

    _publish_sync(
        bus,
        str(job.id),
        EventType.GROUP_STARTED,
        review_id=str(job.review_id),
        group_name=group.name,
        control_count=len(group.controls),
        is_batch=is_batch_mode and len(group.controls) > 1,
    )

    t_group_start = time.time()

    if is_batch_mode and len(group.controls) > 1:
        sub_batches = [
            group.controls[i:i + batch_limit]
            for i in range(0, len(group.controls), batch_limit)
        ]

        eval_results = []
        for batch_idx, sub_batch in enumerate(sub_batches):
            sub_group = ControlGroup(
                name=group.name,
                query=group.query,
                controls=sub_batch,
                group_index=group.group_index,
            )

            if len(sub_batches) > 1:
                print(f"[worker]  → batch {batch_idx + 1}/{len(sub_batches)}: evaluating {len(sub_batch)} controls...")
            else:
                print(f"[worker]  → batch evaluating {len(sub_batch)} controls ({group.name})...")

            batch_results = eval_svc.batch_evaluate(sub_group, formatted_evidence)
            eval_results.extend(batch_results)

        print(f"[worker]  ← batch LLM done ({time.time() - t_group_start:.1f}s for {len(group.controls)} controls)")
        _publish_sync(
            bus,
            str(job.id),
            EventType.GROUP_EVALUATION_COMPLETED,
            review_id=str(job.review_id),
            group_name=group.name,
            elapsed_ms=round((time.time() - t_group_start) * 1000, 1),
        )
    else:
        eval_results = []
        for ctrl in group.controls:
            _publish_sync(
                bus,
                str(job.id),
                EventType.EVALUATION_STARTED,
                review_id=str(job.review_id),
                control_id=ctrl.control_id,
            )
            t_eval_start = time.time()
            eval_result = eval_svc.evaluate(ctrl.name, ctrl.description, formatted_evidence)
            t_eval_end = time.time()
            print(f"[worker]  ← LLM done ({t_eval_end - t_eval_start:.1f}s): {ctrl.control_id} → {eval_result.status}")
            eval_results.append(eval_result)

    for ctrl, eval_result in zip(group.controls, eval_results):
        global_idx += 1
        t_ctrl_start = time.time()
        evidence_texts = [fe.text for fe in formatted_evidence if fe.text]

        grounded_status, grounded_confidence, grounding_warnings = check_grounding(
            eval_result.explanation,
            evidence_texts,
            eval_result.status,
            eval_result.confidence,
        )
        if grounded_status != eval_result.status or grounded_confidence != eval_result.confidence:
            print(f"[worker]  → grounding: {eval_result.status}/{eval_result.confidence:.2f} → {grounded_status}/{grounded_confidence:.2f}")
        eval_result.status = grounded_status
        eval_result.confidence = grounded_confidence
        if grounding_warnings:
            eval_result.explanation += f"\n\n**Grounding Warning:** {grounding_warnings}"

        _publish_sync(
            bus,
            str(job.id),
            EventType.EVALUATION_COMPLETED,
            review_id=str(job.review_id),
            control_id=ctrl.control_id,
            status=eval_result.status,
            confidence=eval_result.confidence,
        )

        evidence_dicts = [fe.to_dict() for fe in formatted_evidence]
        t_ctrl_end = time.time()

        control_eval = ControlEvaluation(
            id=uuid.uuid4(),
            review_id=job.review_id,
            job_id=job.id,
            control_id=ctrl.control_id,
            control_name=ctrl.name,
            control_description=ctrl.description or "",
            status=eval_result.status,
            confidence=eval_result.confidence,
            explanation=eval_result.explanation,
            recommendation=eval_result.recommendation,
            supporting_evidence=json.dumps(evidence_dicts),
            processing_order=global_idx - 1,
            original_query=group.query,
            rewritten_query=rewritten_query,
            retrieval_attempts=retrieval_attempts,
            retrieval_metadata=json.dumps(retrieval_diagnostics.to_dict() if retrieval_diagnostics else {}),
            control_timing_ms=round((t_ctrl_end - t_ctrl_start) * 1000, 1),
        )
        db.add(control_eval)

        stats["total_confidence"] += eval_result.confidence
        if eval_result.status == "implemented":
            stats["implemented"] += 1
        elif eval_result.status == "partially_implemented":
            stats["partial"] += 1

        _publish_sync(
            bus,
            str(job.id),
            EventType.CONTROL_COMPLETED,
            review_id=str(job.review_id),
            control_id=ctrl.control_id,
            control_name=ctrl.name,
            control_description=ctrl.description or "",
            status=eval_result.status,
            confidence=eval_result.confidence,
            explanation=eval_result.explanation,
            recommendation=eval_result.recommendation,
            evidence=evidence_dicts,
            retrieval_metadata=retrieval_diagnostics.to_dict() if retrieval_diagnostics else {},
            original_query=group.query,
            rewritten_query=rewritten_query,
            retrieval_attempts=retrieval_attempts,
            progress=global_idx,
            total=total_controls,
        )

    db.commit()

    _publish_sync(
        bus,
        str(job.id),
        EventType.GROUP_COMPLETED,
        review_id=str(job.review_id),
        group_name=group.name,
        evaluated=len(group.controls),
        elapsed_ms=round((time.time() - t_group_start) * 1000, 1),
    )

    return global_idx


def _run_worker_sync(job_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        bus = get_event_bus()
        retrieval_svc = RetrievalService()
        eval_svc = ComplianceEvaluationService()
        cl_svc = ChecklistService(db)
        grouper = get_control_grouper()

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

        print(f"\n{'='*60}")
        print(f"[worker] GROUPING: mode={settings.evaluation_mode}")
        print(f"{'='*60}")

        groups = grouper.group(controls, strategy=settings.evaluation_mode)

        print(f"\n{'='*60}")
        print(f"[worker] EVALUATION: {len(groups)} groups, {len(controls)} total controls")
        print(f"{'='*60}\n")

        eval_start = time.time()
        stats = {"total_confidence": 0.0, "implemented": 0, "partial": 0}
        global_idx = 0

        for group in groups:
            print(f"\n{'='*60}")
            print(f"[worker] Group {group.group_index + 1}/{len(groups)}: {group.name} ({len(group.controls)} controls)")
            print(f"{'='*60}")

            for ctrl in group.controls:
                global_idx += 1
                print(f"[worker]   [{ctrl.control_id}] {ctrl.name[:60]}")
                _publish_sync(
                    bus,
                    str(job.id),
                    EventType.CONTROL_STARTED,
                    review_id=str(job.review_id),
                    control_id=ctrl.control_id,
                    control_name=ctrl.name,
                    control_description=ctrl.description or "",
                    progress=global_idx - 1,
                    total=len(controls),
                )

            retrieval_result, formatted_evidence, retrieval_attempts, rewritten_query = _retrieve_for_group(
                group, retrieval_svc, bus, job,
            )

            global_idx = _evaluate_group(
                group=group,
                eval_svc=eval_svc,
                formatted_evidence=formatted_evidence,
                retrieval_diagnostics=retrieval_result.diagnostics,
                retrieval_attempts=retrieval_attempts,
                rewritten_query=rewritten_query,
                bus=bus,
                job=job,
                db=db,
                global_idx=global_idx,
                total_controls=len(controls),
                stats=stats,
            )

            job.evaluated_controls = global_idx
            db.commit()

        elapsed = time.time() - eval_start
        avg_conf = stats["total_confidence"] / len(controls) if controls else 0.0
        overall_pct = ((stats["implemented"] + 0.5 * stats["partial"]) / len(controls) * 100) if controls else 0.0

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
        print(f"[worker] Implemented: {stats['implemented']}/{len(controls)} | Partial: {stats['partial']}/{len(controls)}")
        print(f"{'='*60}\n")

        _publish_sync(
            bus,
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
        _publish_sync(
            bus,
            str(job_id),
            EventType.JOB_FAILED,
            error=str(e),
        )

    finally:
        db.close()
