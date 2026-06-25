from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReviewCreate(BaseModel):
    name: str
    description: str = ""


class ReviewUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class EvidenceDocumentResponse(BaseModel):
    id: UUID
    filename: str
    chunk_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ControlResponse(BaseModel):
    id: UUID
    control_id: str
    control_name: str
    control_description: str
    status: str
    confidence: float
    explanation: str
    recommendation: str
    supporting_evidence: list[dict]
    processing_order: int

    model_config = {"from_attributes": True}


class ChecklistResponse(BaseModel):
    id: UUID
    filename: str
    format: str
    status: str
    created_at: datetime
    controls: list[ControlResponse] = []

    model_config = {"from_attributes": True}


class ReviewResponse(BaseModel):
    id: UUID
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    total_controls: int
    evaluated_controls: int
    overall_percentage: float
    average_confidence: float
    processing_time: float
    evidence_documents: list[EvidenceDocumentResponse] = []
    checklist: ChecklistResponse | None = None
    evaluations: list[ControlResponse] = []

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    id: UUID
    name: str
    description: str
    status: str
    created_at: datetime
    total_controls: int
    overall_percentage: float

    model_config = {"from_attributes": True}
