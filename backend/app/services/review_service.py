import uuid
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from app.models.review import ControlEvaluation, EvidenceDocument, Review


class ReviewService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, description: str = "") -> Review:
        review = Review(
            id=uuid.uuid4(),
            name=name,
            description=description,
            status="draft",
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
            )
            .filter(Review.id == review_id)
            .first()
        )

    def update_status(self, review_id: uuid.UUID, status: str) -> Review | None:
        review = self.db.query(Review).filter(Review.id == review_id).first()
        if not review:
            return None
        review.status = status
        review.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(review)
        return review

    def update_summary(
        self,
        review_id: uuid.UUID,
        total_controls: int | None = None,
        evaluated_controls: int | None = None,
        overall_percentage: float | None = None,
        average_confidence: float | None = None,
        processing_time: float | None = None,
    ) -> Review | None:
        review = self.db.query(Review).filter(Review.id == review_id).first()
        if not review:
            return None
        if total_controls is not None:
            review.total_controls = total_controls
        if evaluated_controls is not None:
            review.evaluated_controls = evaluated_controls
        if overall_percentage is not None:
            review.overall_percentage = overall_percentage
        if average_confidence is not None:
            review.average_confidence = average_confidence
        if processing_time is not None:
            review.processing_time = processing_time
        review.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(review)
        return review
