"use client";

import { Clock, FileText, BarChart3 } from "lucide-react";
import { motion } from "framer-motion";
import EmptyState from "@/components/EmptyState";
import type { ReviewListItem } from "@/lib/types";

interface RecentReviewsListProps {
  reviews: ReviewListItem[];
  onSelect: (id: string) => void;
  loading: boolean;
}

const statusColors: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  ready: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  evaluating: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 animate-pulse-amber",
  completed: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  failed: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function RecentReviewsList({ reviews, onSelect, loading }: RecentReviewsListProps) {
  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 transition-colors">
        <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-4">Recent Reviews</h2>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-shimmer rounded-lg h-20 bg-gray-100 dark:bg-gray-800" />
          ))}
        </div>
      </div>
    );
  }

  if (reviews.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 transition-colors">
        <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-4">Recent Reviews</h2>
        <EmptyState
          icon={<FileText className="w-7 h-7" />}
          title="No reviews yet"
          description="Create a new review to start evaluating compliance controls against your evidence."
        />
      </div>
    );
  }

  const container = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: { staggerChildren: 0.06 },
    },
  };

  const item = {
    hidden: { opacity: 0, y: 12 },
    show: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 transition-colors"
    >
      <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-4">Recent Reviews</h2>
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="space-y-3"
      >
        {reviews.map((r) => (
          <motion.button
            key={r.id}
            variants={item}
            whileHover={{ y: -2 }}
            onClick={() => onSelect(r.id)}
            className="w-full text-left bg-gray-50 dark:bg-gray-800/50 hover:bg-amber-50 dark:hover:bg-amber-900/20 border border-gray-100 dark:border-gray-800 rounded-xl p-4 transition-colors group"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-bold text-gray-900 dark:text-gray-100 truncate">
                    {r.name}
                  </span>
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full shrink-0 ${statusColors[r.status] || statusColors.draft}`}>
                    {r.status}
                  </span>
                </div>
                {r.description && (
                  <p className="text-xs text-gray-400 dark:text-gray-500 truncate mb-2">{r.description}</p>
                )}
                <div className="flex items-center gap-4 text-[11px] text-gray-400 dark:text-gray-500">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {timeAgo(r.created_at)}
                  </span>
                  {r.latest_job && (
                    <>
                      <span className="flex items-center gap-1">
                        <BarChart3 className="w-3 h-3" />
                        {r.latest_job.evaluated_controls}/{r.latest_job.total_controls} controls
                      </span>
                      {r.latest_job.status === "completed" && (
                        <span className="font-medium text-amber-600 dark:text-amber-400">
                          {r.latest_job.overall_percentage}% compliant
                        </span>
                      )}
                    </>
                  )}
                </div>
              </div>
              <div className="text-amber-300 dark:text-amber-600 group-hover:text-amber-500 transition-colors shrink-0 mt-0.5">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </motion.button>
        ))}
      </motion.div>
    </motion.div>
  );
}
