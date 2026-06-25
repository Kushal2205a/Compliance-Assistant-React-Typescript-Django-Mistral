"use client";

import { FileText, ClipboardCheck } from "lucide-react";
import BackToReviews from "@/components/BackToReviews";

interface ReviewSummaryProps {
  name: string;
  status: string;
  documentCount: number;
  jobStatus?: string;
}

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  ready: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  evaluating: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 animate-pulse-amber",
  completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  pending: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  running: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 animate-pulse-amber",
};

export default function ReviewSummary({ name, status, documentCount, jobStatus }: ReviewSummaryProps) {
  const displayStatus = jobStatus || status;
  const colorClass = statusColors[displayStatus] || statusColors.draft;

  return (
    <div className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 transition-colors">
      <div className="max-w-5xl mx-auto px-6 py-4">
        <BackToReviews />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">{name}</h1>
            <span className={`text-[11px] font-medium px-2.5 py-0.5 rounded-full ${colorClass}`}>
              {displayStatus}
            </span>
          </div>
          <div className="flex items-center gap-6 text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-1.5">
              <FileText className="w-4 h-4" />
              <span>{documentCount} document{documentCount !== 1 ? "s" : ""}</span>
            </div>
            {displayStatus === "completed" && (
              <div className="flex items-center gap-1.5 text-green-600 dark:text-green-400">
                <ClipboardCheck className="w-4 h-4" />
                <span>Evaluation complete</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
