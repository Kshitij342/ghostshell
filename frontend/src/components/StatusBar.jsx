import React from 'react';
import { RefreshCw, Server, Cpu, AlertTriangle } from 'lucide-react';

export default function StatusBar({
  backendStatus,
  ollamaStatus,
  models,
  selectedModel,
  onSelectModel,
  onRefresh,
  isRefreshing,
}) {
  const isBackendOk = backendStatus?.status === 'healthy';
  const isOllamaOk = ollamaStatus?.connected === true;

  return (
    <div className="status-bar-container">
      {/* Backend Health Badge */}
      <div className="status-badge" title={isBackendOk ? 'FastAPI Backend Healthy' : 'Backend Unreachable'}>
        <Server size={13} color={isBackendOk ? '#00ff9d' : '#f43f5e'} />
        <span>Backend:</span>
        <span
          className={`status-dot ${isBackendOk ? 'connected' : 'disconnected'}`}
        />
        <span>{isBackendOk ? 'Online' : 'Offline'}</span>
      </div>

      {/* Ollama Status Badge */}
      <div
        className="status-badge"
        title={
          isOllamaOk
            ? `Ollama v${ollamaStatus.version || 'ready'} at ${ollamaStatus.base_url}`
            : ollamaStatus?.error || 'Ollama not running'
        }
      >
        <Cpu size={13} color={isOllamaOk ? '#00ff9d' : '#f43f5e'} />
        <span>Ollama:</span>
        <span
          className={`status-dot ${
            isRefreshing ? 'checking' : isOllamaOk ? 'connected' : 'disconnected'
          }`}
        />
        <span>{isOllamaOk ? 'Ready' : 'Offline'}</span>
      </div>

      {/* Model Selector */}
      <div className="status-badge" style={{ marginLeft: 'auto' }}>
        <span>Model:</span>
        <select
          className="model-selector"
          value={selectedModel}
          onChange={(e) => onSelectModel(e.target.value)}
          disabled={!isOllamaOk || models.length === 0}
        >
          {models.length > 0 ? (
            models.map((m) => (
              <option key={m.name} value={m.name}>
                {m.name} {m.parameter_size ? `(${m.parameter_size})` : ''}
              </option>
            ))
          ) : (
            <option value={selectedModel}>{selectedModel}</option>
          )}
        </select>
      </div>

      {/* Manual Refresh Button */}
      <button
        className="refresh-status-btn"
        onClick={onRefresh}
        disabled={isRefreshing}
        title="Check status and refresh model list"
        aria-label="Refresh connection status"
      >
        <RefreshCw
          size={13}
          style={{
            animation: isRefreshing ? 'spin 1s linear infinite' : 'none',
          }}
        />
        <span>{isRefreshing ? 'Checking...' : 'Check'}</span>
      </button>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
