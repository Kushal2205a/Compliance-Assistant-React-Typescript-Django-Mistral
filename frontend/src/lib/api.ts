const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function queryDocument(
  query: string,
  pdf: File,
  onChunk: (text: string) => void,
  onError: (error: string) => void,
  onDone: () => void
): Promise<void> {
  const formData = new FormData();
  formData.append("query", query);
  formData.append("pdf", pdf);

  try {
    const res = await fetch(`${API_BASE}/query/`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: "Request failed" }));
      onError(err.error || `Server responded with ${res.status}`);
      onDone();
      return;
    }

    const reader = res.body?.getReader();
    if (!reader) {
      onError("No response body from server");
      onDone();
      return;
    }

    const decoder = new TextDecoder();
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      onChunk(decoder.decode(value, { stream: true }));
    }
    onDone();
  } catch (err) {
    onError(
      err instanceof Error ? err.message : "Failed to communicate with server"
    );
    onDone();
  }
}
