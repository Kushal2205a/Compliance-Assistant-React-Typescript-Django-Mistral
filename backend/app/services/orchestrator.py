import asyncio
import uuid

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.models.enums import JobStatus, ReviewStatus
from app.models.review import Checklist, EvidenceDocument, Review, ReviewJob


async def check_and_start_evaluation(
    review_id: uuid.UUID,
    db: Session,
) -> ReviewJob | None:
    """Check if both prerequisites are met and start evaluation if so.

    Called after every checklist upload and evidence index completion.
    Returns the started job if both are ready, or None if prerequisites
    are unmet (caller should create a PENDING job separately).
    """
    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        return None

    # --- Evidence check: all documents must be indexed ---
    evidence_docs = (
        db.query(EvidenceDocument)
        .filter(EvidenceDocument.review_id == review_id)
        .all()
    )
    if not evidence_docs:
        return None
    if any(d.status != "indexed" for d in evidence_docs):
        return None

    # --- Checklist check: must exist ---
    checklist = (
        db.query(Checklist)
        .filter(Checklist.review_id == review_id)
        .first()
    )
    if not checklist:
        return None

    # --- Both ready — find or create a PENDING job ---
    active = (
        db.query(ReviewJob)
        .filter(
            ReviewJob.review_id == review_id,
            ReviewJob.status.in_([JobStatus.RUNNING.value, JobStatus.COMPLETED.value]),
        )
        .first()
    )
    if active:
        return active

    job = (
        db.query(ReviewJob)
        .filter(
            ReviewJob.review_id == review_id,
            ReviewJob.status == JobStatus.PENDING.value,
        )
        .first()
    )
    if not job:
        job = ReviewJob(
            id=uuid.uuid4(),
            review_id=review_id,
            checklist_id=checklist.id,
            status=JobStatus.PENDING.value,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

    # Transition review to READY
    if review.status == ReviewStatus.DRAFT.value:
        review.status = ReviewStatus.READY.value
        db.commit()

    # Start worker in background
    from app.services.worker import run_evaluation_worker

    asyncio.create_task(run_evaluation_worker(job.id))

    return job


async def ensure_job_exists(
    review_id: uuid.UUID,
    db: Session,
) -> ReviewJob:
    """Create a PENDING job if none exists. Does NOT require evidence.

    Used when checklist is uploaded before evidence — we want a placeholder
    job that evidence upload can later trigger.
    """
    existing = (
        db.query(ReviewJob)
        .filter(
            ReviewJob.review_id == review_id,
            ReviewJob.status == JobStatus.PENDING.value,
        )
        .first()
    )
    if existing:
        return existing

    checklist = (
        db.query(Checklist)
        .filter(Checklist.review_id == review_id)
        .first()
    )
    job = ReviewJob(
        id=uuid.uuid4(),
        review_id=review_id,
        checklist_id=checklist.id if checklist else None,
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
