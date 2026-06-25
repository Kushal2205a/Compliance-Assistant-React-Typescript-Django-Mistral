from enum import Enum


class ReviewStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    ARCHIVED = "archived"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ControlStatus(str, Enum):
    PENDING = "pending"
    IMPLEMENTED = "implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    MISSING = "missing"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EventType(str, Enum):
    INDEXING_STARTED = "indexing_started"
    INDEXING_COMPLETED = "indexing_completed"
    CONTROL_STARTED = "control_started"
    RETRIEVAL_STARTED = "retrieval_started"
    RETRIEVAL_COMPLETED = "retrieval_completed"
    EVALUATION_STARTED = "evaluation_started"
    EVALUATION_COMPLETED = "evaluation_completed"
    RETRY_STARTED = "retry_started"
    RETRY_COMPLETED = "retry_completed"
    CONTROL_COMPLETED = "control_completed"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
