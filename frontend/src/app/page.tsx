"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ClipboardList } from "lucide-react";
import NewReviewCard from "@/components/dashboard/NewReviewCard";
import RecentReviewsList from "@/components/dashboard/RecentReviewsList";
import ThemeToggle from "@/components/ThemeToggle";
import type { ReviewListItem } from "@/lib/types";

export default function Dashboard() {
  const router = useRouter();
  const [reviews, setReviews] = useState<ReviewListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadReviews = useCallback(async () => {
    setLoading(true);
    try {
      const { listReviews } = await import("@/lib/api");
      const data = await listReviews();
      setReviews(data);
    } catch {
      setReviews([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  const handleReviewCreated = (id: string) => {
    router.push(`/reviews/${id}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 transition-colors">
      <header className="bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 transition-colors">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-amber-500 rounded-lg flex items-center justify-center">
              <ClipboardList className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">
              Compliance Auditor
            </h1>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <NewReviewCard onCreated={handleReviewCreated} />
          <RecentReviewsList
            reviews={reviews}
            onSelect={(id) => router.push(`/reviews/${id}`)}
            loading={loading}
          />
        </div>
      </main>
    </div>
  );
}
