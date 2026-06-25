from datetime import datetime
from uuid import UUID

import json

from pydantic import BaseModel, field_validator


class ReviewCreate(BaseModel):
    name: str
    description: str = ""


class EvidenceDocumentResponse(BaseModel):
    id: UUID
    filename: str
    chunk_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ControlResponse(BaseModel):
    id: UUID
    job_id: UUID | None = None
    control_id: str
    control_name: str
    control_description: str
    status: str
    confidence: float
    explanation: str
    recommendation: str
    supporting_evidence: list[dict] = []
    processing_order: int
    original_query: str = ""
    rewritten_query: str | None = None
    retrieval_attempts: int = 1
    retrieval_metadata: dict = {}
    control_timing_ms: float = 0.0

    model_config = {"from_attributes": True}

    @field_validator("supporting_evidence", mode="before")
    @classmethod
    def parse_supporting_evidence(cls, v):
        if isinstance(v, str):
            return json.loads(v) if v else []
        return v or []

    @field_validator("retrieval_metadata", mode="before")
    @classmethod
    def parse_retrieval_metadata(cls, v):
        if isinstance(v, str):
            return json.loads(v) if v else {}
        return v or {}


class ChecklistResponse(BaseModel):
    id: UUID
    filename: str
    format: str
    status: str
    created_at: datetime
    controls: list[ControlResponse] = []

    model_config = {"from_attributes": True}


class ReviewJobResponse(BaseModel):
    id: UUID
    review_id: UUID
    checklist_id: UUID | None = None
    status: str
    error_message: str | None = None
    total_controls: int
    evaluated_controls: int
    overall_percentage: float
    average_confidence: float
    processing_time: float
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class ReviewResponse(BaseModel):
    id: UUID
    name: str
    description: str
    status: str
    created_at: datetime
    updated_at: datetime
    evidence_documents: list[EvidenceDocumentResponse] = []
    checklist: ChecklistResponse | None = None
    evaluations: list[ControlResponse] = []
    jobs: list[ReviewJobResponse] = []
    orchestration_status: str = "waiting_for_evidence"

    model_config = {"from_attributes": True}


class ReviewListResponse(BaseModel):
    id: UUID
    name: str
    description: str
    status: str
    created_at: datetime
    latest_job: ReviewJobResponse | None = None
    orchestration_status: str = "waiting_for_evidence"

    model_config = {"from_attributes": True}


class ReviewResultsResponse(BaseModel):
    review_id: UUID
    review_name: str
    job: ReviewJobResponse
    summary: dict
    controls: list[ControlResponse]


class JobCreateResponse(BaseModel):
    job_id: UUID
    review_id: UUID
    status: str
