"use client";

import { motion } from "framer-motion";
import { Activity, Search, FileSearch, FileCheck, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import type { SSEEvent } from "@/lib/types";

interface ExecutionTraceProps {
  events: SSEEvent[];
}

const eventConfig: Record<string, { icon: React.ComponentType<{ className?: string }>; color: string; label: string }> = {
  job_created: { icon: Activity, color: "text-gray-400", label: "Job Created" },
  control_started: { icon: Search, color: "text-amber-500", label: "Control Started" },
  retrieval_started: { icon: Search, color: "text-blue-500", label: "Searching Evidence" },
  retrieval_completed: { icon: FileSearch, color: "text-blue-500", label: "Evidence Retrieved" },
  evaluation_started: { icon: FileCheck, color: "text-purple-500", label: "Evaluating" },
  evaluation_completed: { icon: FileCheck, color: "text-purple-500", label: "Evaluated" },
  control_completed: { icon: CheckCircle2, color: "text-green-500", label: "Control Completed" },
  job_completed: { icon: CheckCircle2, color: "text-green-500", label: "Job Completed" },
  job_failed: { icon: XCircle, color: "text-red-500", label: "Job Failed" },
};

function formatTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return ts;
  }
}

export default function ExecutionTrace({ events }: ExecutionTraceProps) {
  if (events.length === 0) {
    return (
      <div className="text-center py-8">
        <Activity className="w-8 h-8 text-gray-200 dark:text-gray-700 mx-auto mb-2" />
        <p className="text-[11px] text-gray-400 dark:text-gray-500">No events yet</p>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="absolute left-[11px] top-3 bottom-3 w-px bg-gray-100 dark:bg-gray-800" />
      <div className="space-y-0">
        {events.map((event, i) => {
          const config = eventConfig[event.event_type] || { icon: Activity, color: "text-gray-400", label: event.event_type };
          const Icon = config.icon;

          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.02 * i }}
              className="relative flex items-start gap-3 py-1.5 pl-6"
            >
              <div className={`absolute left-[5px] w-[14px] h-[14px] rounded-full bg-white dark:bg-gray-900 border-2 flex items-center justify-center ${
                event.event_type === "job_completed"
                  ? "border-green-500"
                  : event.event_type === "job_failed"
                    ? "border-red-500"
                    : "border-amber-400"
              }`}>
                <div className={`w-1.5 h-1.5 rounded-full ${
                  event.event_type === "job_completed"
                    ? "bg-green-500"
                    : event.event_type === "job_failed"
                      ? "bg-red-500"
                      : "bg-amber-400"
                }`} />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <Icon className={`w-3 h-3 ${config.color}`} />
                  <span className="text-[11px] font-medium text-gray-600 dark:text-gray-400">{config.label}</span>
                </div>
                {(event.control_id as string) && (
                  <span className="text-[10px] text-gray-400 dark:text-gray-500 font-mono">{event.control_id as string}</span>
                )}
                {(event.chunks_found as number) != null && (
                  <span className="text-[10px] text-gray-400 dark:text-gray-500 ml-1">
                    {event.chunks_found as number} chunks
                  </span>
                )}
                <div className="text-[9px] text-gray-400 dark:text-gray-500 mt-0.5">
                  {formatTime(event.timestamp)}
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
