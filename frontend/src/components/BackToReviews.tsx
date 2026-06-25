"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

export default function BackToReviews() {
  const router = useRouter();
  return (
    <button
      onClick={() => router.push("/")}
      className="inline-flex items-center gap-1.5 text-xs text-gray-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors mb-3"
    >
      <ArrowLeft className="w-3.5 h-3.5" />
      Back to Reviews
    </button>
  );
}
