/**
 * GhostShell API Client
 * Facilitates communication with the local FastAPI backend.
 */

const API_BASE = '/api';

/**
 * Check backend operational health.
 */
export async function getHealth() {
  const response = await fetch(`${API_BASE}/health`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Backend health check failed: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Check connectivity to the local Ollama daemon.
 */
export async function getOllamaStatus() {
  const response = await fetch(`${API_BASE}/ollama/status`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Failed to query Ollama status: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Fetch available models from Ollama.
 */
export async function getOllamaModels() {
  const response = await fetch(`${API_BASE}/ollama/models`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`Failed to retrieve models: HTTP ${response.status}`);
  }
  return response.json();
}

/**
 * Send a chat, command explanation, or error diagnosis request to the local AI (atomic).
 */
export async function sendChatMessage({ message, mode = 'general', history = [], model = null }) {
  const payload = {
    message,
    mode,
    history: history.slice(-10), // Limit history to last 10 messages
    ...(model ? { model } : {}),
  };

  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
  });

  const data = await response.json();

  if (!response.ok) {
    // If backend returned structured error detail
    const detail = data?.detail || {};
    const errorMsg = typeof detail === 'string' ? detail : detail.message || `Request failed with HTTP ${response.status}`;
    const resolution = detail.resolution || 'Ensure Ollama is running and model is available.';
    const err = new Error(errorMsg);
    err.resolution = resolution;
    err.status = response.status;
    err.type = detail.error || 'ChatError';
    throw err;
  }

  return data;
}

/**
 * Send a chat request with real-time token streaming via Server-Sent Events (SSE).
 */
export async function streamChatMessage({
  message,
  mode = 'general',
  history = [],
  model = null,
  onChunk,
  signal,
}) {
  const payload = {
    message,
    mode,
    history: history.slice(-10),
    ...(model ? { model } : {}),
  };

  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    let errorDetail = `Request failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail?.message || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  if (!response.body) {
    throw new Error('ReadableStream not supported by browser environment.');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep trailing incomplete line in buffer

      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('data: ')) {
          const jsonStr = trimmed.slice(6);
          try {
            const data = JSON.parse(jsonStr);
            if (data.error) {
              const err = new Error(data.message || data.error);
              err.resolution = data.resolution;
              err.type = data.error;
              throw err;
            }
            if (onChunk) {
              onChunk(data);
            }
          } catch (e) {
            if (e.resolution) throw e;
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
