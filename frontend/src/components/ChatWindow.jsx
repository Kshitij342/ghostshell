import React, { useEffect, useRef } from 'react';
import { Trash2, AlertCircle, Terminal, HelpCircle } from 'lucide-react';
import ChatMessage from './ChatMessage';
import GhostAvatar from './GhostAvatar';

export default function ChatWindow({
  messages,
  isLoading,
  ollamaStatus,
  onClearMessages,
  onSampleClick,
}) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const isOllamaConnected = ollamaStatus?.connected === true;

  const starterPrompts = [
    {
      mode: 'command_oracle',
      text: 'Explain: find . -type f -name "*.log" -mtime +30 -exec rm {} \\;',
      label: 'Dissect complex `find` & `exec` command',
    },
    {
      mode: 'error_exorcist',
      text: 'Error: fatal: refusing to merge unrelated histories on git pull origin main',
      label: 'Exorcise git unrelated histories error',
    },
    {
      mode: 'safer_fix',
      text: 'How can I safely kill all node processes using port 3000 on Windows/Linux?',
      label: 'Safe process termination alternatives',
    },
  ];

  return (
    <div className="terminal-window">
      {/* Terminal Title Bar */}
      <div className="terminal-header">
        <div className="terminal-controls">
          <span className="terminal-circle close" />
          <span className="terminal-circle minimize" />
          <span className="terminal-circle maximize" />
        </div>

        <div className="terminal-tab-title">
          <Terminal size={13} color="#00ff9d" />
          <span>ghost@localhost:~$ /bin/ghostshell</span>
        </div>

        <div className="terminal-actions-group">
          {messages.length > 0 && (
            <button
              type="button"
              className="icon-button"
              onClick={onClearMessages}
              title="Clear terminal session"
              aria-label="Clear conversation history"
            >
              <Trash2 size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Offline Alert Banner if Ollama is not connected */}
      {!isOllamaConnected && (
        <div className="offline-banner" role="alert">
          <AlertCircle size={20} color="#f43f5e" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div>
            <div className="offline-banner-title">Ollama Daemon Unreachable</div>
            <div className="offline-banner-body">
              {ollamaStatus?.error || 'GhostShell requires a running local Ollama instance.'}
              <div>
                To start Ollama, run in PowerShell or Terminal:
                <br />
                <code className="offline-command">ollama serve</code>
                <br />
                And ensure your default model is downloaded:
                <br />
                <code className="offline-command">ollama pull qwen2.5:3b</code>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="messages-container" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="empty-terminal-state">
            <div className="ghost-illustration pulse-ghost">
              <GhostAvatar size={64} glowing={true} />
            </div>
            <h2 className="empty-title">The Terminal Ghost is Listening</h2>
            <p className="empty-subtitle">
              Ask about obscure flags, paste terminal exceptions, or request safer command alternatives.
              Powered 100% locally by open-weight AI.
            </p>

            <div className="empty-instructions">
              <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginBottom: '0.2rem' }}>
                Quick queries to test:
              </span>
              {starterPrompts.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="instruction-pill"
                  onClick={() => onSampleClick(item.mode, item.text)}
                >
                  <Terminal size={13} color="#00ff9d" />
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <ChatMessage key={index} message={msg} />
          ))
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="message-row assistant">
            <div className="ghost-thinking">
              <GhostAvatar size={20} glowing={true} className="pulse-ghost" />
              <span>Ghost is analyzing terminal memory...</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
