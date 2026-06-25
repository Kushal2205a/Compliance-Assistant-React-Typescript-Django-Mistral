const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Request failed with status ${res.status}`);
  }
  return res.json();
}

export async function createReview(name: string, description = "") {
  const res = await fetch(`${API_BASE}/reviews`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  return handleResponse<import("./types").Review>(res);
}

export async function listReviews() {
  const res = await fetch(`${API_BASE}/reviews`);
  return handleResponse<import("./types").ReviewListItem[]>(res);
}

export async function getReview(id: string) {
  const res = await fetch(`${API_BASE}/reviews/${id}`);
  return handleResponse<import("./types").Review>(res);
}

export async function uploadEvidence(reviewId: string, files: File[]) {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/evidence`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<import("./types").EvidenceDocument[]>(res);
}

export async function deleteEvidence(reviewId: string, docId: string) {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/evidence/${docId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail || `Delete failed with status ${res.status}`);
  }
}

export async function uploadChecklist(reviewId: string, checklistFile: File) {
  const formData = new FormData();
  formData.append("file", checklistFile);
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/checklist`, {
    method: "POST",
    body: formData,
  });
  return handleResponse<{ job_id: string; review_id: string; status: string }>(res);
}

export async function startEvaluation(reviewId: string, checklistFile: File) {
  return uploadChecklist(reviewId, checklistFile);
}

export function streamJobEvents(
  reviewId: string,
  jobId: string,
  onEvent: (event: import("./types").SSEEvent) => void,
  onError: (error: string) => void,
  onDone: () => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/reviews/${reviewId}/jobs/${jobId}/stream`, {
        signal: controller.signal,
      });
      if (!res.ok) {
        onError(`Stream failed with status ${res.status}`);
        onDone();
        return;
      }
      const reader = res.body?.getReader();
      if (!reader) {
        onError("No response body");
        onDone();
        return;
      }
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;
          const jsonStr = trimmed.slice(6);
          try {
            const data = JSON.parse(jsonStr);
            const eventType = (data.event_type || data.type || "") as string;

            if (eventType === "job_completed" || eventType === "job_failed") {
              onEvent(data as import("./types").SSEEvent);
              onDone();
              return;
            }

            onEvent(data as import("./types").SSEEvent);
          } catch {
            // skip malformed
          }
        }
      }
      onDone();
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onError(err instanceof Error ? err.message : "Stream error");
      }
      onDone();
    }
  })();

  return () => controller.abort();
}

export async function getResults(reviewId: string) {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/results`);
  return handleResponse<import("./types").ReviewResults>(res);
}

export async function getReport(reviewId: string) {
  const res = await fetch(`${API_BASE}/reviews/${reviewId}/report`);
  return handleResponse<Record<string, unknown>>(res);
}

export type ChatCallback = (token: string) => void;

export function streamChat(
  reviewId: string,
  question: string,
  onToken: ChatCallback,
  onError: (error: string) => void,
  onDone: () => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const formData = new FormData();
      formData.append("question", question);

      const res = await fetch(`${API_BASE}/reviews/${reviewId}/chat`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      if (!res.ok) {
        onError(`Chat failed with status ${res.status}`);
        onDone();
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError("No response body");
        onDone();
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(trimmed.slice(6));
            if (data.error) {
              onError(data.error);
              onDone();
              return;
            }
            if (data.token) {
              onToken(data.token);
            }
            if (data.done) {
              onDone();
              return;
            }
          } catch {
            // skip
          }
        }
      }
      onDone();
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onError(err instanceof Error ? err.message : "Chat error");
      }
      onDone();
    }
  })();

  return () => controller.abort();
}
