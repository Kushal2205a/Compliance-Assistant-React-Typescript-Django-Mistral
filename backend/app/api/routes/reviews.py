import json
import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.review import (
    EvidenceDocumentResponse,
    ReviewCreate,
    ReviewListResponse,
    ReviewResponse,
)
from app.services.checklist_service import ChecklistService
from app.services.evaluation_service import EvaluationService
from app.services.evidence_service import EvidenceService
from app.services.review_service import ReviewService

router = APIRouter(prefix="/api/reviews", tags=["reviews"])


@router.post("", response_model=ReviewResponse, status_code=201)
def create_review(body: ReviewCreate, db: Session = Depends(get_db)):
    svc = ReviewService(db)
    return svc.create(name=body.name, description=body.description)


@router.get("", response_model=list[ReviewListResponse])
def list_reviews(db: Session = Depends(get_db)):
    svc = ReviewService(db)
    return svc.list_all()


@router.get("/{review_id}", response_model=ReviewResponse)
def get_review(review_id: uuid.UUID, db: Session = Depends(get_db)):
    svc = ReviewService(db)
    review = svc.get_by_id(review_id)
    if not review:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.post("/{review_id}/evidence", response_model=list[EvidenceDocumentResponse], status_code=201)
def upload_evidence(
    review_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    svc = ReviewService(db)
    review = svc.get_by_id(review_id)
    if not review:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Review not found")

    ev_svc = EvidenceService(db)
    docs = []
    for file in files:
        doc = ev_svc.upload(review_id, file.filename or "document.pdf", file.file)
        doc = ev_svc.index_document(doc)
        docs.append(doc)

    ev_svc.update_review_status(review_id)
    return docs


@router.delete("/{review_id}/evidence/{doc_id}", status_code=204)
def delete_evidence(review_id: uuid.UUID, doc_id: uuid.UUID, db: Session = Depends(get_db)):
    ev_svc = EvidenceService(db)
    if not ev_svc.delete(doc_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Document not found")
    return None


@router.post("/{review_id}/checklist", status_code=201)
def upload_checklist(
    review_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    svc = ReviewService(db)
    if not svc.get_by_id(review_id):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Review not found")

    cl_svc = ChecklistService(db)
    checklist = cl_svc.upload(review_id, file.filename or "checklist.pdf", file.file)
    controls = cl_svc.parse_checklist(checklist.file_path)

    svc.update_status(review_id, "indexing")

    from app.models.review import Checklist as ChecklistModel
    from app.schemas.review import ControlResponse

    evaluation_svc = EvaluationService(db)
    eval_results = []
    for idx, control in enumerate(controls):
        from app.models.review import ControlEvaluation
        stub = ControlEvaluation(
            id=uuid.uuid4(),
            review_id=review_id,
            control_id=control.control_id,
            control_name=control.name,
            control_description=control.description,
            status="pending",
            processing_order=idx,
        )
        db.add(stub)
        eval_results.append(ControlResponse(
            id=stub.id,
            control_id=stub.control_id,
            control_name=stub.control_name,
            control_description=stub.control_description,
            status=stub.status,
            confidence=0.0,
            explanation="",
            recommendation="",
            supporting_evidence=[],
            processing_order=idx,
        ))
    db.commit()

    svc.update_summary(review_id, total_controls=len(controls))

    return {
        "checklist": {
            "id": str(checklist.id),
            "filename": checklist.filename,
            "format": checklist.format,
            "status": checklist.status,
            "controls": [r.model_dump() for r in eval_results],
        }
    }


@router.post("/{review_id}/evaluate")
def start_evaluation(review_id: uuid.UUID, db: Session = Depends(get_db)):
    svc = ReviewService(db)
    review = svc.get_by_id(review_id)
    if not review:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Review not found")

    from app.services.checklist_service import ChecklistService
    cl_svc = ChecklistService(db)
    checklist = (
        db.query(type(review).checklist.property.mapper.class_)
        .filter(type(review).checklist.property.mapper.class_.review_id == review_id)
        .first()
    )
    # Re-read checklist from DB
    from app.models.review import Checklist
    checklist_obj = db.query(Checklist).filter(Checklist.review_id == review_id).first()
    if not checklist_obj:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="No checklist uploaded")

    controls = cl_svc.parse_checklist(checklist_obj.file_path)

    from app.models.review import ControlEvaluation
    db.query(ControlEvaluation).filter(ControlEvaluation.review_id == review_id).delete()
    db.commit()

    ev_svc = EvaluationService(db)

    def event_stream():
        for event in ev_svc.evaluate_controls(review_id, controls):
            yield f"data: {event}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{review_id}/report")
def get_report(review_id: uuid.UUID, db: Session = Depends(get_db)):
    svc = ReviewService(db)
    review = svc.get_by_id(review_id)
    if not review:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Review not found")

    from app.models.review import ControlEvaluation
    evaluations = (
        db.query(ControlEvaluation)
        .filter(ControlEvaluation.review_id == review_id)
        .order_by(ControlEvaluation.processing_order)
        .all()
    )

    controls = []
    for ev in evaluations:
        controls.append({
            "id": str(ev.id),
            "control_id": ev.control_id,
            "control_name": ev.control_name,
            "status": ev.status,
            "confidence": ev.confidence,
            "explanation": ev.explanation,
            "recommendation": ev.recommendation,
            "supporting_evidence": json.loads(ev.supporting_evidence) if ev.supporting_evidence else [],
        })

    from app.models.review import EvidenceDocument
    evidence_docs = (
        db.query(EvidenceDocument)
        .filter(EvidenceDocument.review_id == review_id)
        .all()
    )

    return {
        "review_id": str(review_id),
        "review_name": review.name,
        "status": review.status,
        "summary": {
            "total_controls": review.total_controls,
            "evaluated_controls": review.evaluated_controls,
            "overall_percentage": review.overall_percentage,
            "average_confidence": review.average_confidence,
            "processing_time": review.processing_time,
            "documents_analyzed": len(evidence_docs),
        },
        "controls": controls,
    }


@router.post("/{review_id}/chat")
def chat_followup(review_id: uuid.UUID, question: str = Form(...), db: Session = Depends(get_db)):
    from app.services.chat_service import ChatService
    chat_svc = ChatService(db)

    def event_stream():
        for event in chat_svc.ask(review_id, question):
            yield f"data: {event}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
