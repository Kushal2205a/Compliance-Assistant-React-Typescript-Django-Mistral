"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import ReviewSummary from "@/components/workspace/ReviewSummary";
import EvidenceUpload from "@/components/workspace/EvidenceUpload";
import EvaluationDashboard from "@/components/workspace/EvaluationDashboard";
import ExecutionTrace from "@/components/workspace/ExecutionTrace";
import FollowUpChat from "@/components/workspace/FollowUpChat";
import ThemeToggle from "@/components/ThemeToggle";
import type { Review, ReviewJob, ControlEvaluation, SSEEvent } from "@/lib/types";
import { getReview, streamJobEvents, getResults } from "@/lib/api";

export default function AuditWorkspace() {
  const params = useParams();
  const router = useRouter();
  const reviewId = params.id as string;

  const [review, setReview] = useState<Review | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activeJob, setActiveJob] = useState<ReviewJob | null>(null);
  const [controls, setControls] = useState<ControlEvaluation[]>([]);
  const [isEvaluating, _setIsEvaluating] = useState(false);
  const isEvaluatingRef = useRef(false);
  const setIsEvaluating = (v: boolean) => { isEvaluatingRef.current = v; _setIsEvaluating(v); };
  const [traceEvents, setTraceEvents] = useState<SSEEvent[]>([]);
  const [showTrace, setShowTrace] = useState(false);

  const cancelStreamRef = useRef<(() => void) | null>(null);

  const handleStreamEvent = useCallback((event: SSEEvent, jobId: string) => {
    setTraceEvents((prev) => [...prev, event]);

    if (event.control_id && event.event_type === "control_completed") {
      setControls((prev) => [
        ...prev,
        {
          id: event.control_id as string,
          job_id: jobId,
          control_id: event.control_id as string,
          control_name: event.control_name as string,
          control_description: (event.control_description as string) ?? "",
          status: event.status as ControlEvaluation["status"],
          confidence: event.confidence as number,
          explanation: event.explanation as string,
          recommendation: (event.recommendation as string) || "",
          supporting_evidence: (event.evidence as ControlEvaluation["supporting_evidence"]) || [],
          processing_order: (event.progress as number) - 1,
          original_query: (event.original_query as string) ?? "",
          rewritten_query: (event.rewritten_query as string | null) ?? null,
          retrieval_attempts: (event.retrieval_attempts as number) ?? 1,
          retrieval_metadata: (event.retrieval_metadata as Record<string, unknown>) ?? {},
        },
      ]);
    }

    if (event.event_type === "job_completed" || event.event_type === "job_failed") {
      setIsEvaluating(false);
      getResults(reviewId).then((results) => {
        setControls(results.controls);
        setActiveJob(results.job);
      }).catch(console.error);
    }
  }, [reviewId]);

  const connectStream = useCallback((jobId: string) => {
    cancelStreamRef.current?.();
    cancelStreamRef.current = streamJobEvents(
      reviewId,
      jobId,
      (event) => handleStreamEvent(event, jobId),
      (err) => {
        console.error("Stream error:", err);
        setIsEvaluating(false);
      },
      () => {
        if (isEvaluatingRef.current) {
          getResults(reviewId).then((results) => {
            setControls(results.controls);
            setActiveJob(results.job);
          }).catch(console.error);
          setIsEvaluating(false);
        }
      },
    );
  }, [reviewId, handleStreamEvent]);

  const loadReview = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getReview(reviewId);
      const prevStatus = review?.orchestration_status;
      setReview(data);

      if (data.orchestration_status === "evaluating") {
        const runningJob = data.jobs?.find(
          (j) => j.status === "running" || j.status === "pending",
        );
        if (runningJob) {
          setActiveJob(runningJob);
          setControls([]);
          setTraceEvents([]);
          setShowTrace(true);
          if (!isEvaluatingRef.current) {
            setIsEvaluating(true);
            connectStream(runningJob.id);
          }
        }
      } else if (data.orchestration_status === "completed") {
        const completedJob = data.jobs?.find((j) => j.status === "completed");
        if (completedJob) {
          setActiveJob(completedJob);
          setIsEvaluating(false);
          const results = await getResults(reviewId);
          setControls(results.controls);
        }
      } else {
        if (prevStatus === "evaluating" || isEvaluatingRef.current) {
          setIsEvaluating(false);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load review");
    } finally {
      setLoading(false);
    }
  }, [reviewId, connectStream]);

  useEffect(() => {
    loadReview();
    return () => cancelStreamRef.current?.();
  }, [loadReview]);

  const handleChecklistUpload = useCallback(async (_file: File) => {
    await loadReview();
  }, [loadReview]);

  const handleDocumentsChange = useCallback(() => {
    loadReview();
  }, [loadReview]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center transition-colors">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-gray-400 dark:text-gray-500">Loading review...</p>
        </div>
      </div>
    );
  }

  if (error || !review) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center transition-colors">
        <div className="text-center">
          <p className="text-sm text-red-500 mb-3">{error || "Review not found"}</p>
          <button onClick={() => router.push("/")} className="text-sm text-amber-600 dark:text-amber-400 hover:underline">
            Back to dashboard
          </button>
        </div>
      </div>
    );
  }

  const orchStatus = review.orchestration_status;
  const showEvidenceUpload = orchStatus === "waiting_for_evidence" || orchStatus === "indexing_documents" || orchStatus === "waiting_for_checklist";
  const showEvaluation = orchStatus === "evaluating" || orchStatus === "completed" || controls.length > 0;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex flex-col transition-colors">
      <ReviewSummary
        name={review.name}
        status={review.status}
        documentCount={review.evidence_documents?.length || 0}
        jobStatus={activeJob?.status}
      />

      <div className="flex-1 flex min-h-0">
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-5xl mx-auto p-6 space-y-6">
            {showEvidenceUpload && (
              <EvidenceUpload
                reviewId={reviewId}
                documents={review.evidence_documents || []}
                onDocumentsChange={handleDocumentsChange}
                disabled={isEvaluating}
              />
            )}

            {showEvaluation && (
              <EvaluationDashboard
                job={activeJob}
                controls={controls}
                evidenceCount={review.evidence_documents?.length || 0}
                isEvaluating={isEvaluating}
              />
            )}

            {orchStatus === "waiting_for_checklist" && !isEvaluating && (
              <div className="text-center py-8">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  All evidence indexed. Attach a compliance checklist in the panel below to begin evaluation.
                </p>
              </div>
            )}

            {orchStatus === "waiting_for_evidence" && !isEvaluating && (
              <div className="text-center py-16">
                <svg className="mx-auto h-12 w-12 text-gray-200 dark:text-gray-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <h3 className="mt-4 text-sm font-medium text-gray-900 dark:text-gray-100">Upload evidence documents</h3>
                <p className="mt-1 text-sm text-gray-400 dark:text-gray-500">
                  Upload PDF documents above, then attach a compliance checklist to begin evaluation.
                </p>
              </div>
            )}
          </div>
        </div>

        <AnimatePresence>
          {showTrace && (
            <motion.div
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 280, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
              className="bg-white dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 overflow-hidden shrink-0"
            >
              <div className="w-[280px] h-full overflow-y-auto">
                <div className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      Execution Trace
                    </h3>
                    <button
                      onClick={() => setShowTrace(false)}
                      className="text-gray-300 dark:text-gray-600 hover:text-gray-500 transition-colors"
                    >
                      <PanelRightClose className="w-4 h-4" />
                    </button>
                  </div>
                  <ExecutionTrace events={traceEvents} />
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {!showTrace && (
          <button
            onClick={() => setShowTrace(true)}
            className="fixed right-0 top-1/2 -translate-y-1/2 bg-white dark:bg-gray-900 border border-r-0 rounded-l-lg px-2 py-8 text-xs text-gray-400 hover:text-amber-500 dark:hover:text-amber-400 z-10 transition-colors"
            title="Show execution trace"
          >
            <PanelRightOpen className="w-4 h-4" />
          </button>
        )}
      </div>

      <div className={`border-t border-gray-200 dark:border-gray-800 ${orchStatus === "completed" ? "h-80" : "h-64"}`}>
        <FollowUpChat
          reviewId={reviewId}
          hasCompletedJob={orchStatus === "completed"}
          isEvaluating={isEvaluating}
          onChecklistAttached={handleChecklistUpload}
        />
      </div>
    </div>
  );
}
