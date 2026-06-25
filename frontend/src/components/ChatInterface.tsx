"use client";

import { useState, useRef, useCallback } from "react";
import { queryDocument } from "@/lib/api";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const handleSend = async () => {
    const query = input.trim();
    if (!query || !file) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: query },
      { role: "assistant", content: "" },
    ]);
    setInput("");
    setProgress([]);
    setLoading(true);
    scrollToBottom();

    let accumulated = "";

    queryDocument(
      query,
      file,
      (chunk) => {
        accumulated += chunk;
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant") {
            updated[updated.length - 1] = {
              role: "assistant",
              content: accumulated,
            };
          }
          return updated;
        });
      },
      (error) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last?.role === "assistant" && !last.content) {
            updated[updated.length - 1] = {
              role: "assistant",
              content: `Error: ${error}`,
            };
          }
          return updated;
        });
      },
      () => setLoading(false)
    );
  };

  return (
    <div className="flex flex-col flex-1 min-h-0 gap-3 pb-4">
      <div className="relative w-full">
        <input
          type="text"
          value={file?.name || ""}
          placeholder="Upload a PDF document..."
          readOnly
          className="w-full border rounded-full py-2 px-4 pr-12 text-sm focus:outline-none cursor-default bg-gray-50"
        />
        <label className="absolute right-2 top-1/2 -translate-y-1/2 bg-yellow-500 hover:bg-yellow-600 text-white rounded-full w-8 h-8 flex items-center justify-center cursor-pointer transition-colors">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 20 20"
            fill="currentColor"
            className="w-4 h-4"
          >
            <path d="M9.25 13.25a.75.75 0 0 0 1.5 0V4.636l2.955 3.129a.75.75 0 0 0 1.09-1.03l-4.25-4.5a.75.75 0 0 0-1.09 0l-4.25 4.5a.75.75 0 1 0 1.09 1.03L9.25 4.636V13.25Z" />
            <path d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z" />
          </svg>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="hidden"
          />
        </label>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 rounded-lg bg-gray-50 border">
        <div className="p-4 space-y-4">
          {messages.length === 0 && !loading && (
            <p className="text-gray-400 text-sm text-center pt-8">
              Upload a PDF and ask a question to get started.
            </p>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[80%] rounded-xl px-4 py-2 whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-yellow-500 text-white rounded-br-md"
                    : "bg-white border rounded-bl-md"
                }`}
              >
                {msg.content || (
                  <span className="text-gray-400 italic">Thinking...</span>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !loading) handleSend();
          }}
          placeholder={
            file ? "Ask something about this document..." : "Upload a PDF first"
          }
          disabled={!file}
          className="flex-1 border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-yellow-400 disabled:opacity-50"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || !file || loading}
          className="bg-yellow-500 hover:bg-yellow-600 disabled:bg-gray-300 text-white px-6 py-2 rounded-lg text-sm font-medium transition-colors"
        >
          {loading ? "..." : "Ask"}
        </button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span className="inline-block w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
          Streaming response...
        </div>
      )}
    </div>
  );
}
