export async function streamChat({ url, token, body, onDelta, onDone, onError }) {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");

  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE frames end with blank line
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";

    for (const frame of frames) {
      const line = frame.trim();
      if (!line.startsWith("data:")) continue;

      const jsonStr = line.slice(5).trim();
      if (!jsonStr) continue;

      const evt = JSON.parse(jsonStr);

      if (evt.type === "delta") onDelta?.(evt.delta);
      if (evt.type === "done") {
        onDone?.();
        return;
      }
      if (evt.type === "error") throw new Error(evt.message || "stream error");
    }
  }
}
