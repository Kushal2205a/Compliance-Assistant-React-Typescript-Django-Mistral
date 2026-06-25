"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import { motion } from "framer-motion";

interface NewReviewCardProps {
  onCreated: (id: string) => void;
}

export default function NewReviewCard({ onCreated }: NewReviewCardProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const { createReview } = await import("@/lib/api");
      const review = await createReview(name.trim(), description.trim());
      setName("");
      setDescription("");
      onCreated(review.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create review");
    } finally {
      setCreating(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-6 transition-colors"
    >
      <div className="mb-4">
        <h2 className="text-sm font-bold text-gray-900 dark:text-gray-100">New Review</h2>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Create a new compliance review</p>
      </div>

      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
        placeholder="Review name..."
        className="w-full border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent mb-2 transition-colors"
      />
      <input
        type="text"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
        placeholder="Description (optional)..."
        className="w-full border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 rounded-lg px-4 py-2.5 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent mb-3 transition-colors"
      />

      {error && (
        <p className="text-xs text-red-500 mb-3">{error}</p>
      )}

      <button
        onClick={handleSubmit}
        disabled={!name.trim() || creating}
        className="w-full flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-600 disabled:bg-gray-200 dark:disabled:bg-gray-700 text-white disabled:text-gray-400 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors"
      >
        <Plus className="w-4 h-4" />
        {creating ? "Creating..." : "Create Review"}
      </button>
    </motion.div>
  );
}
