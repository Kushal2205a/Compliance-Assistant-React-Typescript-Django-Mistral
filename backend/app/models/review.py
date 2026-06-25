import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.models.enums import ControlStatus, JobStatus, ReviewStatus


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(String(50), default=ReviewStatus.DRAFT.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    evidence_documents = relationship("EvidenceDocument", back_populates="review", cascade="all, delete-orphan")
    checklist = relationship("Checklist", back_populates="review", uselist=False, cascade="all, delete-orphan")
    evaluations = relationship("ControlEvaluation", back_populates="review", cascade="all, delete-orphan")
    jobs = relationship("ReviewJob", back_populates="review", cascade="all, delete-orphan")


class EvidenceDocument(Base):
    __tablename__ = "evidence_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    doc_hash = Column(String(64), default="")
    chunk_count = Column(Integer, default=0)
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("Review", back_populates="evidence_documents")


class Checklist(Base):
    __tablename__ = "checklists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False, unique=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    format = Column(String(10), default="pdf")
    status = Column(String(50), default="uploaded")
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("Review", back_populates="checklist")


class ReviewJob(Base):
    __tablename__ = "review_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    checklist_id = Column(UUID(as_uuid=True), ForeignKey("checklists.id"), nullable=True)
    status = Column(String(50), default=JobStatus.PENDING.value)
    error_message = Column(Text, nullable=True)

    total_controls = Column(Integer, default=0)
    evaluated_controls = Column(Integer, default=0)
    overall_percentage = Column(Float, default=0.0)
    average_confidence = Column(Float, default=0.0)
    processing_time = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    review = relationship("Review", back_populates="jobs")
    checklist = relationship("Checklist")
    evaluations = relationship("ControlEvaluation", back_populates="job", cascade="all, delete-orphan")


class ControlEvaluation(Base):
    __tablename__ = "control_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("review_jobs.id"), nullable=True)
    control_id = Column(String(100), default="")
    control_name = Column(String(255), nullable=False)
    control_description = Column(Text, default="")
    status = Column(String(50), default=ControlStatus.PENDING.value)
    confidence = Column(Float, default=0.0)
    explanation = Column(Text, default="")
    recommendation = Column(Text, default="")
    supporting_evidence = Column(Text, default="[]")
    processing_order = Column(Integer, default=0)
    original_query = Column(Text, default="")
    rewritten_query = Column(Text, nullable=True)
    retrieval_attempts = Column(Integer, default=1)
    retrieval_metadata = Column(Text, default="{}")
    control_timing_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("Review", back_populates="evaluations")
    job = relationship("ReviewJob", back_populates="evaluations")
