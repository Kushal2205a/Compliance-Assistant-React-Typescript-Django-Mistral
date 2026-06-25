"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Paperclip, Copy, Check, MessageSquare, Clock } from "lucide-react";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import { streamChat, uploadChecklist } from "@/lib/api";
import type { SSEEvent, ControlEvaluation } from "@/lib/types";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface FollowUpChatProps {
  reviewId: string;
  hasCompletedJob: boolean;
  isEvaluating: boolean;
  onChecklistAttached: (file: File) => void;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2">
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="w-1.5 h-1.5 bg-amber-400 rounded-full"
          style={{
            animation: `bounce-dot 1.4s ease-in-out ${i * 0.16}s infinite`,
          }}
        />
      ))}
    </div>
  );
}

export default function FollowUpChat({
  reviewId,
  hasCompletedJob,
  isEvaluating,
  onChecklistAttached,
}: FollowUpChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;

    const userMsg: ChatMessage = { role: "user", content: question, timestamp: new Date() };
    const assistantMsg: ChatMessage = { role: "assistant", content: "", timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setLoading(true);
    setError(null);

    let accumulated = "";

    streamChat(
      reviewId,
      question,
      (token) => {
        accumulated += token;
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = { ...last, content: accumulated };
          }
          return updated;
        });
      },
      (err) => {
        setError(err);
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant" && !last.content) {
            updated[updated.length - 1] = { ...last, content: `Error: ${err}` };
          }
          return updated;
        });
        setLoading(false);
      },
      () => setLoading(false)
    );
  };

  const handleAttachChecklist = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setLoading(true);
      setError(null);
      onChecklistAttached(file);

      await uploadChecklist(reviewId, file);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload checklist");
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (content: string, index: number) => {
    await navigator.clipboard.writeText(content);
    setCopiedId(index);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const canChat = hasCompletedJob && !isEvaluating;
  const canAttachChecklist = !hasCompletedJob && !isEvaluating;

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800 transition-colors">
      <div className="flex items-center gap-2 px-5 py-3 border-b border-gray-100 dark:border-gray-800">
        <MessageSquare className="w-4 h-4 text-amber-500" />
        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
          {canAttachChecklist ? "Attach Checklist" : "Audit Questions"}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="max-w-3xl mx-auto px-4 py-4 space-y-4">
          {messages.length === 0 && !error && (
            <div className="text-center py-8 max-w-md mx-auto">
              <MessageSquare className="w-10 h-10 text-gray-200 dark:text-gray-700 mx-auto mb-3" />
              {canChat && (
                <>
                  <p className="text-xs text-gray-500 dark:text-gray-400 font-medium mb-3">
                    Evaluation complete. Ask follow-up questions about:
                  </p>
                  <div className="flex flex-wrap justify-center gap-1.5">
                    {["evidence", "controls", "confidence", "compliance decisions"].map((tag) => (
                      <span
                        key={tag}
                        className="text-[10px] bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 px-2 py-1 rounded-full border border-amber-100 dark:border-amber-800"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </>
              )}
              {canAttachChecklist && (
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  Attach a compliance checklist PDF to start evaluating your evidence.
                </p>
              )}
              {isEvaluating && (
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  Evaluation in progress. Chat will be available once complete.
                </p>
              )}
            </div>
          )}

          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 12, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                transition={{ duration: 0.2 }}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`relative group max-w-[75%] ${
                    msg.role === "user" ? "order-1" : "order-2"
                  }`}
                >
                  <div
                    className={`rounded-2xl px-4 py-2.5 whitespace-pre-wrap text-sm ${
                      msg.role === "user"
                        ? "bg-amber-500 text-white rounded-br-md"
                        : "bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-bl-md"
                    }`}
                  >
                    {msg.role === "assistant" && msg.content ? (
                      <div className="prose-custom max-w-none">
                        <MarkdownRenderer content={msg.content} />
                      </div>
                    ) : msg.role === "assistant" && loading && i === messages.length - 1 ? (
                      <TypingIndicator />
                    ) : (
                      msg.content || (
                        <span className="text-gray-400 italic">Thinking...</span>
                      )
                    )}
                    {msg.content && msg.role === "assistant" && (
                      <button
                        onClick={() => handleCopy(msg.content, i)}
                        className="absolute -bottom-5 right-0 p-1 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Copy response"
                      >
                        {copiedId === i ? (
                          <Check className="w-3 h-3 text-green-500" />
                        ) : (
                          <Copy className="w-3 h-3 text-gray-400 hover:text-amber-500" />
                        )}
                      </button>
                    )}
                  </div>
                  <div className={`flex items-center gap-1 mt-1 ${msg.role === "user" ? "justify-end pr-1" : "justify-start pl-1"}`}>
                    <Clock className="w-2.5 h-2.5 text-gray-300 dark:text-gray-600" />
                    <span className="text-[10px] text-gray-300 dark:text-gray-600">{formatTime(msg.timestamp)}</span>
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {error && (
            <div className="text-center text-xs text-red-500 bg-red-50 dark:bg-red-900/20 rounded-lg px-4 py-2">{error}</div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="border-t border-gray-100 dark:border-gray-800 p-3">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !loading) handleSend(); }}
              placeholder={
                isEvaluating
                  ? "Waiting for evaluation to complete..."
                  : canChat
                    ? "Ask a follow-up question..."
                    : canAttachChecklist
                      ? "Attach a checklist to begin"
                      : ""
              }
              disabled={!canChat || loading}
              className="flex-1 border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 rounded-xl px-4 py-2.5 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            />

            {canAttachChecklist && (
              <>
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={loading}
                  className="bg-amber-500 hover:bg-amber-600 disabled:bg-gray-200 dark:disabled:bg-gray-700 text-white disabled:text-gray-400 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center gap-1.5"
                >
                  <Paperclip className="w-4 h-4" />
                  Attach
                </button>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={handleAttachChecklist}
                />
              </>
            )}

            {canChat && (
              <button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="bg-amber-500 hover:bg-amber-600 disabled:bg-gray-200 dark:disabled:bg-gray-700 text-white disabled:text-gray-400 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors flex items-center gap-1.5"
              >
                <Send className="w-4 h-4" />
                Send
              </button>
            )}
          </div>

          {loading && (
            <div className="flex items-center gap-2 mt-2 text-[10px] text-amber-600 dark:text-amber-400">
              <span className="inline-block w-1.5 h-1.5 bg-amber-500 rounded-full animate-pulse" />
              {isEvaluating ? "Evaluation in progress..." : "Streaming response..."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
