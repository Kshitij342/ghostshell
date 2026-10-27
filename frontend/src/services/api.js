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
 * Send a chat, command explanation, or error diagnosis request to the local AI.
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
