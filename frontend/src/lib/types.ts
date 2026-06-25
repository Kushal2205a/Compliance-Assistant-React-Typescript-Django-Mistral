export interface Review {
  id: string;
  name: string;
  description: string;
  status: "draft" | "ready" | "archived";
  created_at: string;
  updated_at: string;
  evidence_documents: EvidenceDocument[];
  checklist: Checklist | null;
  evaluations: ControlEvaluation[];
  jobs: ReviewJob[];
  orchestration_status: OrchestrationStatus;
}

export interface ReviewListItem {
  id: string;
  name: string;
  description: string;
  status: string;
  created_at: string;
  latest_job: ReviewJob | null;
  orchestration_status: OrchestrationStatus;
}

export interface EvidenceDocument {
  id: string;
  filename: string;
  chunk_count: number;
  status: string;
  created_at: string;
}

export interface Checklist {
  id: string;
  filename: string;
  format: string;
  status: string;
  created_at: string;
  controls: ControlEvaluation[];
}

export interface ReviewJob {
  id: string;
  review_id: string;
  checklist_id: string | null;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  error_message: string | null;
  total_controls: number;
  evaluated_controls: number;
  overall_percentage: number;
  average_confidence: number;
  processing_time: number;
  created_at: string;
  completed_at: string | null;
}

export interface ControlEvaluation {
  id: string;
  job_id: string | null;
  control_id: string;
  control_name: string;
  control_description: string;
  status: "implemented" | "partially_implemented" | "missing" | "insufficient_evidence" | "pending";
  confidence: number;
  explanation: string;
  recommendation: string;
  supporting_evidence: EvidenceRef[];
  processing_order: number;
  original_query?: string;
  rewritten_query?: string | null;
  retrieval_attempts?: number;
  retrieval_metadata?: Record<string, unknown>;
  control_timing_ms?: number;
}

export interface EvidenceRef {
  document_id: string;
  filename: string;
  page: number | null;
  section: string | null;
  chunk_id: string;
  similarity_score: number;
  quoted_text: string;
  text?: string;
  excerpt?: string;
  strength?: string;
}

export interface ReviewResults {
  review_id: string;
  review_name: string;
  job: ReviewJob;
  summary: {
    total_controls: number;
    evaluated_controls: number;
    overall_percentage: number;
    average_confidence: number;
    processing_time: number;
    documents_analyzed: number;
  };
  controls: ControlEvaluation[];
}

export interface SSEEvent {
  event_type: string;
  timestamp: string;
  [key: string]: unknown;
}

export type OrchestrationStatus =
  | "waiting_for_evidence"
  | "indexing_documents"
  | "waiting_for_checklist"
  | "evaluating"
  | "completed";

export type WorkspaceState = "empty" | "evidence_upload" | "ready" | "evaluating" | "complete";
