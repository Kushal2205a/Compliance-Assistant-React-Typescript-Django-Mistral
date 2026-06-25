"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronDown,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Search,
  FileSearch,
  FileCheck,
  Lightbulb,
  MessageSquareText,
  Quote,
} from "lucide-react";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import type { ControlEvaluation } from "@/lib/types";

interface ControlRowProps {
  control: ControlEvaluation;
  isEvaluating?: boolean;
  stage?: "searching" | "retrieving" | "evaluating" | "completed";
}

const statusConfig: Record<string, { icon: React.ComponentType<{ className?: string }>; label: string; badge: string }> = {
  implemented: {
    icon: CheckCircle2,
    label: "Implemented",
    badge: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 border border-amber-200 dark:border-amber-700",
  },
  partially_implemented: {
    icon: AlertTriangle,
    label: "Partial",
    badge: "bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400 border border-amber-200 dark:border-amber-700 border-dashed",
  },
  missing: {
    icon: HelpCircle,
    label: "Missing",
    badge: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800",
  },
  insufficient_evidence: {
    icon: HelpCircle,
    label: "Insufficient",
    badge: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border border-gray-200 dark:border-gray-700",
  },
  pending: {
    icon: HelpCircle,
    label: "Pending",
    badge: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400",
  },
};

const confidenceBadge = (pct: number): { label: string; cls: string } => {
  if (pct >= 80) return { label: "High", cls: "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400 border border-green-200 dark:border-green-800" };
  if (pct >= 50) return { label: "Medium", cls: "bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400 border border-amber-200 dark:border-amber-700" };
  return { label: "Low", cls: "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400 border border-gray-200 dark:border-gray-700" };
};

const evidenceScoreLabel = (score: number): string => {
  if (score >= 0.7) return "Strong";
  if (score >= 0.4) return "Moderate";
  return "Weak";
};

const evidenceScoreColor = (score: number): string => {
  if (score >= 0.7) return "bg-green-50 text-green-700 dark:bg-green-900/20 dark:text-green-400";
  if (score >= 0.4) return "bg-amber-50 text-amber-600 dark:bg-amber-900/20 dark:text-amber-400";
  return "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400";
};

const stageSteps = [
  { key: "searching", icon: Search, label: "Searching" },
  { key: "retrieving", icon: FileSearch, label: "Retrieving Evidence" },
  { key: "evaluating", icon: FileCheck, label: "Evaluating" },
  { key: "completed", icon: CheckCircle2, label: "Completed" },
];

const _STRENGTH_SCORE: Record<string, number> = { Strong: 0.9, Moderate: 0.6, Weak: 0.3 };

function linkCitations(text: string): string {
  return text.replace(/\[Evidence\s+(\d+)\]/g, (_, n) => `[Evidence ${n}](#evidence-${n})`);
}

function EvidenceCard({ evidence, idx }: { evidence: ControlEvaluation["supporting_evidence"][0]; idx: number }) {
  const [expanded, setExpanded] = useState(false);
  const score = evidence.similarity_score ?? _STRENGTH_SCORE[evidence.strength ?? ""] ?? 0.5;
  const scoreCls = evidenceScoreColor(score);
  const text = evidence.text ?? evidence.excerpt ?? evidence.quoted_text ?? "";
  const preview = text.slice(0, 300);
  const isLong = text.length > 300;

  return (
    <motion.div
      id={`evidence-${idx + 1}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 rounded-lg p-3"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="min-w-0">
          <p className="text-xs font-medium text-amber-700 dark:text-amber-400 truncate">
            {evidence.filename}
          </p>
          <div className="flex items-center gap-2 text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">
            {evidence.page != null && <span>Page {evidence.page}</span>}
            {evidence.section && <span className="text-amber-500">· {evidence.section}</span>}
          </div>
        </div>
        <span className={`shrink-0 text-[10px] font-medium px-2 py-0.5 rounded-full ${scoreCls}`}>
          {evidenceScoreLabel(score)}
        </span>
      </div>
      {!expanded && (
        <div className="flex items-center gap-2 text-[10px] text-gray-400 dark:text-gray-500 mb-1.5">
          <span>Evidence Score: {(score * 100).toFixed(0)}%</span>
        </div>
      )}
      <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
        {expanded ? text : `"${preview}${isLong ? "..." : ""}"`}
      </p>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-[11px] text-amber-600 dark:text-amber-400 hover:underline mt-1"
        >
          {expanded ? "Show less" : "Show full context"}
        </button>
      )}
    </motion.div>
  );
}

export default function ControlRow({ control, isEvaluating, stage }: ControlRowProps) {
  const [expanded, setExpanded] = useState(false);
  const config = statusConfig[control.status] || statusConfig.pending;
  const confidencePct = Math.round(control.confidence * 100);
  const confBadge = confidenceBadge(confidencePct);

  const StatusIcon = config.icon;

  const renderStageAnimation = () => {
    const currentStage = stage || "completed";
    const currentIdx = stageSteps.findIndex((s) => s.key === currentStage);

    return (
      <div className="flex items-center gap-2 py-1">
        {stageSteps.map((s, i) => {
          const StepIcon = s.icon;
          const isActive = i === currentIdx && isEvaluating;
          const isPast = i < currentIdx || (!isEvaluating && currentStage === "completed");
          return (
            <div key={s.key} className="flex items-center gap-1.5">
              <div
                className={`flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium transition-all ${
                  isActive
                    ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 animate-pulse"
                    : isPast
                      ? "bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-400"
                }`}
              >
                <StepIcon className="w-3 h-3" />
                <span>{s.label}</span>
              </div>
              {i < stageSteps.length - 1 && (
                <div className={`w-3 h-px ${isPast ? "bg-green-400" : "bg-gray-200 dark:bg-gray-700"}`} />
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <motion.div
      layout
      className={`border rounded-lg overflow-hidden transition-colors ${
        expanded ? "border-amber-200 dark:border-amber-800" : "border-gray-100 dark:border-gray-800"
      }`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 bg-white dark:bg-gray-900 hover:bg-amber-50/50 dark:hover:bg-amber-900/10 transition-colors text-left"
      >
        <div className="shrink-0 text-gray-300 dark:text-gray-600">
          <StatusIcon className={`w-4 h-4 ${
            control.status === "implemented" ? "text-green-500" :
            control.status === "partially_implemented" ? "text-amber-500" :
            control.status === "missing" ? "text-red-400" : "text-gray-400"
          }`} />
        </div>
        <div className="flex-1 min-w-0 flex flex-col gap-0.5">
          <span className="text-[11px] font-mono text-gray-400 dark:text-gray-500">
            {control.control_id}
          </span>
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100 line-clamp-2" title={control.control_name}>
            {control.control_name}
          </span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${config.badge}`}>
            {config.label}
          </span>
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${confBadge.cls}`}>
            {confBadge.label} ({confidencePct}%)
          </span>
          <span className="text-[10px] text-gray-400 dark:text-gray-500 whitespace-nowrap">
            Evidence ({control.supporting_evidence.length})
          </span>
          {isEvaluating && renderStageAnimation()}
          <motion.div
            animate={{ rotate: expanded ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="w-4 h-4 text-gray-300 dark:text-gray-600" />
          </motion.div>
        </div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-3 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800 space-y-3">
              <div className="flex items-center gap-3">
                <span className={`text-[11px] font-medium px-2 py-1 rounded-full ${config.badge}`}>
                  <StatusIcon className="w-3.5 h-3.5 inline mr-1" />
                  {config.label}
                </span>
              </div>

              <div>
                <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                  <MessageSquareText className="w-3.5 h-3.5 text-amber-500" />
                  Explanation
                </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                    <MarkdownRenderer content={linkCitations(control.explanation)} />
                  </div>
              </div>

              {control.recommendation && (
                <div>
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
                    Recommendation
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                    <MarkdownRenderer content={linkCitations(control.recommendation)} />
                  </div>
                </div>
              )}

              {control.retrieval_metadata && Object.keys(control.retrieval_metadata).length > 0 && (
                <details className="group">
                  <summary className="flex items-center gap-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5 cursor-pointer hover:text-amber-600 dark:hover:text-amber-400">
                    <ChevronDown className="w-3.5 h-3.5 text-amber-500 group-open:rotate-0 -rotate-90 transition-transform" />
                    Retrieval Details
                  </summary>
                  {(() => {
                    const m = control.retrieval_metadata as Record<string, unknown>;
                    const countItems: Array<{ label: string; key: string; suffix?: string }> = [
                      { label: "Dense", key: "dense_results", suffix: " results" },
                      { label: "BM25", key: "bm25_results", suffix: " results" },
                      { label: "RRF", key: "rrf_results", suffix: " fused" },
                      { label: "Reranked", key: "reranked_results", suffix: " chunks" },
                      { label: "Boilerplate removed", key: "boilerplate_removed" },
                      { label: "Expanded", key: "expanded_contexts", suffix: " contexts" },
                      { label: "Final sent", key: "final_chunks_sent", suffix: " chunks" },
                    ];
                    const timeItems: Array<{ label: string; key: string; suffix?: string }> = [
                      { label: "Dense search", key: "dense_search_ms", suffix: "ms" },
                      { label: "BM25 search", key: "bm25_search_ms", suffix: "ms" },
                      { label: "Reranker", key: "reranker_ms", suffix: "ms" },
                      { label: "Context expansion", key: "expansion_ms", suffix: "ms" },
                      { label: "Boilerplate filter", key: "boilerplate_ms", suffix: "ms" },
                      { label: "LLM eval", key: "llm_ms", suffix: "ms" },
                      { label: "Total", key: "total_ms", suffix: "ms" },
                    ];
                    return (
                      <div className="mt-2 space-y-2">
                        <div className="grid grid-cols-2 gap-1.5 text-[11px] text-gray-500 dark:text-gray-400">
                          {countItems
                            .filter((it) => m[it.key] != null)
                            .map((it) => (
                              <span key={it.key}>
                                {it.label}: {String(m[it.key])}{it.suffix ?? ""}
                              </span>
                            ))}
                        </div>
                        <div className="grid grid-cols-2 gap-1.5 text-[11px] text-gray-500 dark:text-gray-400">
                          {timeItems
                            .filter((it) => m[it.key] != null)
                            .map((it) => (
                              <span key={it.key}>
                                {it.label}: {String(m[it.key])}{it.suffix ?? ""}
                              </span>
                            ))}
                        </div>
                        {(!!m.embedding_model || !!m.retrieval_strategy) && (
                          <div className="text-[11px] text-gray-400 dark:text-gray-500">
                            <span className="font-medium text-gray-500 dark:text-gray-400">Strategy:</span> {`${m.retrieval_strategy ?? "—"}`}
                            <span className="ml-2">| Embeddings: {`${m.embedding_model ?? ""}`}</span>
                            {!!m.reranker_model && <span className="ml-2">| Reranker: {`${m.reranker_model}`}</span>}
                          </div>
                        )}
                        {(control.original_query || control.rewritten_query) && (
                          <div className="text-[11px] text-gray-400 dark:text-gray-500 space-y-0.5">
                            {control.original_query && (
                              <p><span className="font-medium text-gray-500 dark:text-gray-400">Query:</span> {control.original_query}</p>
                            )}
                            {control.rewritten_query && (
                              <p><span className="font-medium text-gray-500 dark:text-gray-400">Rewritten:</span> {control.rewritten_query}</p>
                            )}
                            {control.retrieval_attempts != null && control.retrieval_attempts > 1 && (
                              <p><span className="font-medium text-gray-500 dark:text-gray-400">Attempts:</span> {String(control.retrieval_attempts)}</p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </details>
              )}

              {control.supporting_evidence.length > 0 && (
                <div>
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1.5">
                    <Quote className="w-3.5 h-3.5 text-amber-500" />
                    Key Citations
                    <span className="text-gray-400 dark:text-gray-500 font-normal">
                      ({control.supporting_evidence.length})
                    </span>
                  </div>
                  <div className="space-y-2">
                    {control.supporting_evidence.map((ev, i) => (
                      <EvidenceCard key={ev.chunk_id || i} evidence={ev} idx={i} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
