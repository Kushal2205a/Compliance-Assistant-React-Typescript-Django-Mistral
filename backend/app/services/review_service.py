import uuid

from sqlalchemy.orm import Session, joinedload

from app.models.enums import JobStatus, ReviewStatus
from app.models.review import Review


def compute_orchestration_status(review: Review) -> str:
    """Derive the frontend-facing orchestration state from review data.

    States: waiting_for_evidence | indexing_documents | waiting_for_checklist
            | evaluating | completed
    """
    evidence_docs = getattr(review, "evidence_documents", []) or []
    jobs = getattr(review, "jobs", []) or []

    # Check for completed/failed job first
    completed_job = next(
        (j for j in jobs if j.status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value)),
        None,
    )
    if completed_job:
        return "completed"

    # Check for running evaluation
    running_job = next(
        (j for j in jobs if j.status == JobStatus.RUNNING.value),
        None,
    )
    if running_job:
        return "evaluating"

    # Evidence status
    if not evidence_docs:
        return "waiting_for_evidence"
    if any(d.status != "indexed" for d in evidence_docs):
        return "indexing_documents"

    # Evidence all indexed — check for checklist
    if not review.checklist:
        return "waiting_for_checklist"

    # Both ready but no running/completed job (worker may start imminently)
    return "evaluating"


class ReviewService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, description: str = "") -> Review:
        review = Review(
            id=uuid.uuid4(),
            name=name,
            description=description,
            status=ReviewStatus.DRAFT.value,
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def list_all(self) -> list[Review]:
        return (
            self.db.query(Review)
            .order_by(Review.created_at.desc())
            .all()
        )

    def get_by_id(self, review_id: uuid.UUID) -> Review | None:
        return (
            self.db.query(Review)
            .options(
                joinedload(Review.evidence_documents),
                joinedload(Review.checklist),
                joinedload(Review.evaluations),
                joinedload(Review.jobs),
            )
            .filter(Review.id == review_id)
            .first()
        )

    def transition_status(self, review_id: uuid.UUID, target: ReviewStatus) -> Review | None:
        valid_transitions = {
            ReviewStatus.DRAFT: [ReviewStatus.READY],
            ReviewStatus.READY: [ReviewStatus.ARCHIVED],
            ReviewStatus.ARCHIVED: [],
        }

        review = self.db.query(Review).filter(Review.id == review_id).first()
        if not review:
            return None

        current = ReviewStatus(review.status)
        if current == target:
            return review
        if target not in valid_transitions.get(current, []):
            raise ValueError(
                f"Cannot transition from {current.value} to {target.value}"
            )

        review.status = target.value
        self.db.commit()
        self.db.refresh(review)
        return review
