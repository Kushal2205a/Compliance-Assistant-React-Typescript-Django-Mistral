import json
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.enums import EventType, JobStatus
from app.models.review import Checklist, ControlEvaluation, EvidenceDocument, Review, ReviewJob
from app.schemas.review import (
    ControlResponse,
    EvidenceDocumentResponse,
    JobCreateResponse,
    ReviewCreate,
    ReviewJobResponse,
    ReviewListResponse,
    ReviewResponse,
    ReviewResultsResponse,
)
from app.services.checklist_service import ChecklistService
from app.services.chat_service import ChatService
from app.services.evidence_service import EvidenceService
from app.services.orchestrator import check_and_start_evaluation, ensure_job_exists
from app.services.review_service import ReviewService, compute_orchestration_status

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("", response_model=ReviewResponse, status_code=201)
def create_review(body: ReviewCreate, db: Session = Depends(get_db)):
    svc = ReviewService(db)
    return svc.create(name=body.name, description=body.description)


@router.get("", response_model=list[ReviewListResponse])
def list_reviews(db: Session = Depends(get_db)):
    svc = ReviewService(db)
    reviews = svc.list_all()
    result = []
    for r in reviews:
        d = {
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "status": r.status,
            "created_at": r.created_at,
            "latest_job": r.jobs[0] if r.jobs else None,
            "orchestration_status": compute_orchestration_status(r),
        }
        result.append(d)
    return result


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(review_id: uuid.UUID, db: Session = Depends(get_db)):
    from fastapi import HTTPException

    svc = ReviewService(db)
    review = svc.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    data = ReviewResponse.model_validate(review)
    data.orchestration_status = compute_orchestration_status(review)
    return data


@router.post("/{review_id}/evidence", response_model=list[EvidenceDocumentResponse], status_code=201)
async def upload_evidence(
    review_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException

    svc = ReviewService(db)
    review = svc.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    ev_svc = EvidenceService(db)
    docs = []
    for file in files:
        doc = ev_svc.upload(review_id, file.filename or "document.pdf", file.file)
        doc = ev_svc.index_document(doc)
        docs.append(doc)

    ev_svc.update_review_status(review_id)

    # Check if both prerequisites are met and auto-start evaluation
    await check_and_start_evaluation(review_id, db)

    return docs


@router.delete("/{review_id}/evidence/{doc_id}", status_code=204)
def delete_evidence(review_id: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db)):
    from fastapi import HTTPException

    ev_svc = EvidenceService(db)
    if not ev_svc.delete(doc_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return None


@router.post("/{review_id}/checklist", response_model=JobCreateResponse, status_code=201)
async def upload_checklist(
    review_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a compliance checklist. Evaluation auto-starts when evidence is also ready."""
    from fastapi import HTTPException

    svc = ReviewService(db)
    review = svc.get_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    cl_svc = ChecklistService(db)
    cl_svc.upload(review_id, file.filename or "checklist.pdf", file.file)

    # Ensure a PENDING job exists even if evidence isn't ready yet
    job = await ensure_job_exists(review_id, db)

    # Try to start evaluation if both prerequisites are met
    started = await check_and_start_evaluation(review_id, db)
    if started:
        job = started

    return JobCreateResponse(
        job_id=job.id,
        review_id=review_id,
        status=job.status,
    )


@router.post("/{review_id}/evaluate", response_model=JobCreateResponse, status_code=201)
async def legacy_upload_checklist(
    review_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Legacy alias — delegates to the checklist endpoint."""
    return await upload_checklist(review_id, file=file, db=db)


@router.get("/{review_id}/jobs", response_model=list[ReviewJobResponse])
def list_jobs(review_id: uuid.UUID, db: Session = Depends(get_db)):
    jobs = (
        db.query(ReviewJob)
        .filter(ReviewJob.review_id == review_id)
        .order_by(ReviewJob.created_at.desc())
        .all()
    )
    return jobs


@router.get("/{review_id}/jobs/{job_id}/stream")
async def stream_job(job_id: uuid.UUID, db: Session = Depends(get_db)):
    from fastapi import HTTPException

    job = db.query(ReviewJob).filter(ReviewJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    from app.services.event_bus import get_event_bus

    bus = get_event_bus()

    async def event_stream():
        async for event in bus.subscribe(str(job_id)):
            yield event

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{review_id}/results", response_model=ReviewResultsResponse)
def get_results(review_id: uuid.UUID, db: Session = Depends(get_db)):
    from fastapi import HTTPException

    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    latest_job = (
        db.query(ReviewJob)
        .filter(
            ReviewJob.review_id == review_id,
            ReviewJob.status == JobStatus.COMPLETED.value,
        )
        .order_by(ReviewJob.created_at.desc())
        .first()
    )

    if not latest_job:
        raise HTTPException(status_code=404, detail="No completed evaluation found")

    evaluations = (
        db.query(ControlEvaluation)
        .filter(ControlEvaluation.job_id == latest_job.id)
        .order_by(ControlEvaluation.processing_order)
        .all()
    )

    evidence_docs = (
        db.query(EvidenceDocument)
        .filter(EvidenceDocument.review_id == review_id)
        .all()
    )

    controls = [ControlResponse.model_validate(ev) for ev in evaluations]

    return ReviewResultsResponse(
        review_id=review_id,
        review_name=review.name,
        job=ReviewJobResponse.model_validate(latest_job),
        summary={
            "total_controls": latest_job.total_controls,
            "evaluated_controls": latest_job.evaluated_controls,
            "overall_percentage": latest_job.overall_percentage,
            "average_confidence": latest_job.average_confidence,
            "processing_time": latest_job.processing_time,
            "documents_analyzed": len(evidence_docs),
        },
        controls=controls,
    )


@router.get("/{review_id}/report")
def get_report(review_id: uuid.UUID, db: Session = Depends(get_db)):
    from fastapi import HTTPException

    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    latest_job = (
        db.query(ReviewJob)
        .filter(
            ReviewJob.review_id == review_id,
            ReviewJob.status == JobStatus.COMPLETED.value,
        )
        .order_by(ReviewJob.created_at.desc())
        .first()
    )

    if not latest_job:
        raise HTTPException(status_code=404, detail="No completed evaluation found")

    evaluations = (
        db.query(ControlEvaluation)
        .filter(ControlEvaluation.job_id == latest_job.id)
        .order_by(ControlEvaluation.processing_order)
        .all()
    )

    evidence_docs = (
        db.query(EvidenceDocument)
        .filter(EvidenceDocument.review_id == review_id)
        .all()
    )

    controls = []
    for ev in evaluations:
        controls.append({
            "id": str(ev.id),
            "job_id": str(ev.job_id) if ev.job_id else None,
            "control_id": ev.control_id,
            "control_name": ev.control_name,
            "status": ev.status,
            "confidence": ev.confidence,
            "explanation": ev.explanation,
            "recommendation": ev.recommendation,
            "supporting_evidence": json.loads(ev.supporting_evidence) if ev.supporting_evidence else [],
        })

    return {
        "review_id": str(review_id),
        "review_name": review.name,
        "job_id": str(latest_job.id),
        "status": latest_job.status,
        "summary": {
            "total_controls": latest_job.total_controls,
            "evaluated_controls": latest_job.evaluated_controls,
            "overall_percentage": latest_job.overall_percentage,
            "average_confidence": latest_job.average_confidence,
            "processing_time": latest_job.processing_time,
            "documents_analyzed": len(evidence_docs),
        },
        "controls": controls,
    }


@router.post("/{review_id}/chat")
def chat_followup(review_id: uuid.UUID, question: str = Form(...), db: Session = Depends(get_db)):
    chat_svc = ChatService(db)

    def event_stream():
        for event in chat_svc.ask(review_id, question):
            yield f"data: {event}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
