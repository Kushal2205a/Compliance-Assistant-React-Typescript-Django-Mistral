"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import AnimatedCounter from "@/components/AnimatedCounter";
import ControlRow from "./ControlRow";
import EmptyState from "@/components/EmptyState";
import type { ControlEvaluation, ReviewJob } from "@/lib/types";

interface EvaluationDashboardProps {
  job: ReviewJob | null;
  controls: ControlEvaluation[];
  evidenceCount: number;
  isEvaluating: boolean;
}

const confidenceLabel = (pct: number): string => {
  if (pct >= 80) return "High";
  if (pct >= 50) return "Medium";
  return "Low";
};

const confidenceColor = (pct: number): string => {
  if (pct >= 80) return "text-green-600 dark:text-green-400";
  if (pct >= 50) return "text-amber-600 dark:text-amber-400";
  return "text-gray-500 dark:text-gray-400";
};

const computeScore = (controls: ControlEvaluation[]): number => {
  if (controls.length === 0) return 0;
  let implemented = 0;
  let partial = 0;
  for (const c of controls) {
    if (c.status === "implemented") implemented++;
    else if (c.status === "partially_implemented") partial++;
  }
  return ((implemented + 0.5 * partial) / controls.length) * 100;
};

const computeAvgConfidence = (controls: ControlEvaluation[]): number => {
  if (controls.length === 0) return 0;
  return controls.reduce((sum, c) => sum + c.confidence, 0) / controls.length;
};

const evidenceCoverage = (controls: ControlEvaluation[]): string => {
  const withEvidence = controls.filter((c) => c.supporting_evidence.length > 0).length;
  if (controls.length === 0) return "0%";
  return `${Math.round((withEvidence / controls.length) * 100)}%`;
};

export default function EvaluationDashboard({ job, controls, isEvaluating, evidenceCount }: EvaluationDashboardProps) {
  const hasData = controls.length > 0;
  const [filter, setFilter] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState<string | null>(null);

  const filteredControls = filter
    ? controls.filter((c) => c.status === filter)
    : controls;

  const sortedControls = [...filteredControls].sort((a, b) => {
    if (sortBy === "confidence") return b.confidence - a.confidence;
    return a.processing_order - b.processing_order;
  });

  const scoreVal = controls.length > 0 ? computeScore(controls) : (job?.overall_percentage ?? 0);
  const avgConf = controls.length > 0 ? computeAvgConfidence(controls) : (job?.average_confidence ?? 0);
  const withEv = controls.filter((c) => c.supporting_evidence.length > 0).length;

  const cards = job || controls.length > 0
    ? [
        {
          label: "Compliance Score",
          sublabel: `${controls.length} / ${controls.length} Controls`,
          value: scoreVal,
          suffix: "%",
          decimals: 0,
          isActive: filter === "implemented",
        },
        {
          label: "Controls Evaluated",
          sublabel: `${Math.round(avgConf * 100)}% avg confidence`,
          value: controls.length,
          suffix: ` / ${controls.length}`,
          decimals: 0,
          isActive: false,
        },
        {
          label: "Evidence Confidence",
          sublabel: `${confidenceLabel(Math.round(avgConf * 100))} — ${Math.round(avgConf * 100)}%`,
          value: Math.round(avgConf * 100),
          suffix: "%",
          decimals: 0,
          isActive: sortBy === "confidence",
        },
        {
          label: "Evaluation Time",
          sublabel: `${(job?.processing_time ?? 0).toFixed(1)} seconds`,
          value: job?.processing_time ?? 0,
          suffix: " s",
          decimals: 1,
          isActive: false,
        },
        {
          label: "Evidence Coverage",
          sublabel: `${withEv} / ${controls.length} controls with evidence`,
          value: parseInt(evidenceCoverage(controls)),
          suffix: "%",
          decimals: 0,
          isActive: false,
        },
      ]
    : [];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-gray-700 dark:text-gray-300">
          Evaluation Results
          {isEvaluating && (
            <span className="text-[11px] text-amber-600 dark:text-amber-400 animate-pulse font-medium">
              Running...
            </span>
          )}
        </h2>
        {filter && (
          <button
            onClick={() => setFilter(null)}
            className="text-[11px] text-amber-600 dark:text-amber-400 hover:underline"
          >
            Clear filter
          </button>
        )}
      </div>

      {isEvaluating && !hasData && (
        <div className="text-center py-10 text-sm text-gray-400">
          <div className="inline-flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
            <span className="text-amber-600 dark:text-amber-400 font-medium">Evaluating controls against evidence...</span>
          </div>
        </div>
      )}

      {hasData && job && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3"
        >
          {cards.map((card, i) => (
            <motion.button
              key={card.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
              whileHover={i === 0 || i === 2 ? { y: -2 } : undefined}
              onClick={i === 0 ? () => setFilter(filter === "implemented" ? null : "implemented") : i === 2 ? () => setSortBy(sortBy === "confidence" ? null : "confidence") : undefined}
              disabled={i !== 0 && i !== 2}
              type="button"
              className={`bg-white dark:bg-gray-900 border rounded-xl px-4 py-4 text-center transition-all ${
                card.isActive
                  ? "border-amber-400 ring-1 ring-amber-400"
                  : "border-gray-200 dark:border-gray-800 hover:border-amber-200 dark:hover:border-amber-700"
              } ${i === 0 || i === 2 ? "cursor-pointer" : "cursor-default"}`}
            >
              <div className={`text-xl font-bold text-gray-900 dark:text-gray-100 font-mono ${confidenceColor(card.value)}`}>
                <AnimatedCounter
                  from={0}
                  to={card.value}
                  suffix={card.suffix}
                  decimals={card.decimals}
                />
              </div>
              <div className="text-[11px] font-medium text-gray-500 dark:text-gray-400 mt-0.5">{card.label}</div>
              <div className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5 truncate">{card.sublabel}</div>
            </motion.button>
          ))}
        </motion.div>
      )}

      {hasData && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="space-y-1.5"
        >
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
              Control Results
            </div>
            {sortBy === "confidence" && (
              <span className="text-[10px] text-amber-600 dark:text-amber-400">Sorted by confidence</span>
            )}
          </div>
          <div className="space-y-1 max-h-[30rem] overflow-y-auto">
            {sortedControls.map((c, i) => (
              <motion.div
                key={c.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 + i * 0.04 }}
              >
                <ControlRow control={c} isEvaluating={isEvaluating && c.status === "pending"} />
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {!isEvaluating && !hasData && (
        <EmptyState
          icon={
            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          }
          title="No evaluation results"
          description="Attach a compliance checklist to start evaluating controls against your evidence."
        />
      )}
    </div>
  );
}
