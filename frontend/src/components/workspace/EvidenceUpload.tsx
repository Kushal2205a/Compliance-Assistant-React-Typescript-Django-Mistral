"use client";

import { useState, useRef, useCallback } from "react";
import { Upload, File, Trash2, CheckCircle2, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { EvidenceDocument } from "@/lib/types";

interface EvidenceUploadProps {
  reviewId: string;
  documents: EvidenceDocument[];
  onDocumentsChange: () => void;
  disabled?: boolean;
}

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

export default function EvidenceUpload({ reviewId, documents, onDocumentsChange, disabled }: EvidenceUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(async (files: FileList) => {
    const pdfFiles = Array.from(files).filter((f) => f.name.endsWith(".pdf"));
    if (pdfFiles.length === 0) return;
    setUploading(true);
    try {
      const { uploadEvidence } = await import("@/lib/api");
      await uploadEvidence(reviewId, pdfFiles);
      onDocumentsChange();
    } catch (err) {
      console.error("Upload failed:", err);
    } finally {
      setUploading(false);
    }
  }, [reviewId, onDocumentsChange]);

  const handleDelete = useCallback(async (docId: string) => {
    try {
      const { deleteEvidence } = await import("@/lib/api");
      await deleteEvidence(reviewId, docId);
      onDocumentsChange();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  }, [reviewId, onDocumentsChange]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl p-5 transition-colors"
    >
      <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 mb-3">Evidence Documents</h3>

      <div
        onDragOver={(e) => { e.preventDefault(); if (!disabled) setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={async (e) => { e.preventDefault(); setIsDragOver(false); if (!disabled && e.dataTransfer.files) await handleFiles(e.dataTransfer.files); }}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
          isDragOver
            ? "border-amber-400 bg-amber-50 dark:bg-amber-900/20"
            : disabled
              ? "border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50 cursor-not-allowed"
              : "border-gray-200 dark:border-gray-700 hover:border-amber-300 dark:hover:border-amber-700 hover:bg-amber-50/50 dark:hover:bg-amber-900/10"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          className="hidden"
          disabled={disabled}
          onChange={async (e) => { if (e.target.files) await handleFiles(e.target.files); e.target.value = ""; }}
        />
        <Upload className={`w-8 h-8 mx-auto mb-2 ${isDragOver ? "text-amber-500" : "text-gray-300 dark:text-gray-600"}`} />
        <p className={`text-sm font-medium ${isDragOver ? "text-amber-600 dark:text-amber-400" : "text-gray-500 dark:text-gray-400"}`}>
          {uploading ? "Uploading..." : "Drop PDF files here or click to browse"}
        </p>
        <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Only PDF files are supported</p>
      </div>

      <AnimatePresence>
        {documents.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 space-y-2"
          >
            {documents.map((doc) => (
              <motion.div
                key={doc.id}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 12 }}
                className="flex items-center justify-between bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 rounded-lg px-4 py-3 group"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <File className="w-5 h-5 text-amber-500 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">{doc.filename}</p>
                    <div className="flex items-center gap-3 text-[11px] text-gray-400 dark:text-gray-500 mt-0.5">
                      <span>{timeAgo(doc.created_at)}</span>
                      {doc.status === "indexed" ? (
                        <span className="flex items-center gap-1 text-green-600 dark:text-green-400">
                          <CheckCircle2 className="w-3 h-3" />
                          {doc.chunk_count} chunks
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          {doc.status}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
                  className="p-2 text-gray-300 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                  title="Delete document"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
