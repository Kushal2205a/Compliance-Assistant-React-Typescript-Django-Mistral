import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.base import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(String(50), default="draft")  # draft, indexing, ready, evaluating, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    total_controls = Column(Integer, default=0)
    evaluated_controls = Column(Integer, default=0)
    overall_percentage = Column(Float, default=0.0)
    average_confidence = Column(Float, default=0.0)
    processing_time = Column(Float, default=0.0)

    evidence_documents = relationship("EvidenceDocument", back_populates="review", cascade="all, delete-orphan")
    checklist = relationship("Checklist", back_populates="review", uselist=False, cascade="all, delete-orphan")
    evaluations = relationship("ControlEvaluation", back_populates="review", cascade="all, delete-orphan")


class EvidenceDocument(Base):
    __tablename__ = "evidence_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    doc_hash = Column(String(64), default="")
    chunk_count = Column(Integer, default=0)
    status = Column(String(50), default="pending")  # pending, indexing, indexed, failed
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("Review", back_populates="evidence_documents")


class Checklist(Base):
    __tablename__ = "checklists"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False, unique=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    format = Column(String(10), default="pdf")  # pdf, docx, xlsx, csv
    status = Column(String(50), default="uploaded")
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("Review", back_populates="checklist")


class ControlEvaluation(Base):
    __tablename__ = "control_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    control_id = Column(String(100), default="")
    control_name = Column(String(255), nullable=False)
    control_description = Column(Text, default="")
    status = Column(String(50), default="pending")
    # implemented, partially_implemented, missing, insufficient_evidence
    confidence = Column(Float, default=0.0)
    explanation = Column(Text, default="")
    recommendation = Column(Text, default="")
    supporting_evidence = Column(Text, default="[]")  # JSON list
    processing_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    review = relationship("Review", back_populates="evaluations")
