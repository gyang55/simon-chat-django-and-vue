export async function streamChat({
  url,
  token,
  body,
  onDelta,
  onDone,
  onError,
}) {
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": "application/json",
      "Accept": "text/event-stream",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || "Streaming request failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");

  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE events end with \n\n
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";

    for (const part of parts) {
      if (!part.startsWith("data:")) continue;

      const json = part.replace("data:", "").trim();
      if (!json) continue;

      const event = JSON.parse(json);

      if (event.type === "delta") {
        onDelta?.(event.delta);
      }

      if (event.type === "done") {
        onDone?.();
        return;
      }

      if (event.type === "error") {
        throw new Error(event.message);
      }
    }
  }
}
