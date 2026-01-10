export async function streamChat({ url, token, body, onDelta, onDone }) {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: token ? `Bearer ${token}` : "",
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body ?? {}),
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(txt || `HTTP ${res.status}`);
  }

  if (!res.body) throw new Error("No response body (streaming not supported)");

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");

  let buf = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buf += decoder.decode(value, { stream: true });

    // SSE events separated by blank line
    const events = buf.split("\n\n");
    buf = events.pop() || "";

    for (const evt of events) {
      // handle multi-line SSE event; we only care about data:
      const lines = evt.split("\n");
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;

        const data = line.slice(5).trimStart(); // remove "data:" and one space if present

        if (data === "[DONE]") {
          onDone?.();
          return;
        }

        onDelta?.(data);
      }
    }
  }

  onDone?.();
}
