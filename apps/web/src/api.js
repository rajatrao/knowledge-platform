export async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (response.status === 204) return null;
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.detail || response.statusText);
    error.status = response.status;
    throw error;
  }
  return payload;
}

export async function askStream(path, body, onStage) {
  const response = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/x-ndjson",
    },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const error = new Error(payload.detail || response.statusText);
    error.status = response.status;
    throw error;
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finished = false;
  let result = null;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.trim()) continue;
      const message = JSON.parse(line);
      if (message.stage) {
        onStage(message.stage);
        await new Promise((resolve) => setTimeout(resolve, 40));
      }
      if (message.error) {
        const error = new Error(message.error);
        error.status = message.status;
        throw error;
      }
      if (message.done) {
        result = message.result ?? null;
        await new Promise((resolve) => setTimeout(resolve, 280));
        finished = true;
      }
    }
  }
  if (!finished) throw new Error("Ask failed");
  return result;
}
