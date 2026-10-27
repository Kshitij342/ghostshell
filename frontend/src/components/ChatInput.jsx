import React, { useRef, useEffect } from 'react';
import { Send, X, CornerDownLeft, Sparkles, Terminal, ShieldAlert } from 'lucide-react';

export default function ChatInput({
  input,
  setInput,
  onSend,
  isLoading,
  activeMode,
  onResetMode,
  placeholder,
  isOllamaConnected,
}) {
  const textareaRef = useRef(null);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  }, [input]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && input.trim()) {
        onSend();
      }
    }
  };

  const getModeLabel = (mode) => {
    switch (mode) {
      case 'command_oracle':
        return { label: 'Command Oracle', icon: Terminal, color: '#00ff9d' };
      case 'error_exorcist':
        return { label: 'Error Exorcist', icon: ShieldAlert, color: '#f43f5e' };
      case 'safer_fix':
        return { label: 'Safer Fix', icon: Sparkles, color: '#38bdf8' };
      default:
        return null;
    }
  };

  const modeInfo = getModeLabel(activeMode);

  return (
    <div className="terminal-input-bar">
      {modeInfo && (
        <div className="active-mode-indicator">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: modeInfo.color }}>
            <modeInfo.icon size={13} />
            <span>Active Mode: <strong>{modeInfo.label}</strong></span>
          </div>
          <button
            type="button"
            className="mode-dismiss-btn"
            onClick={onResetMode}
            title="Reset to general terminal mode"
          >
            <X size={12} />
            <span>Switch to General</span>
          </button>
        </div>
      )}

      <form
        className="input-form"
        onSubmit={(e) => {
          e.preventDefault();
          if (!isLoading && input.trim()) {
            onSend();
          }
        }}
      >
        <div className="prompt-prefix">ghost@terminal:~$</div>

        <textarea
          ref={textareaRef}
          className="terminal-textarea"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            !isOllamaConnected
              ? 'Ollama is offline. Start it with "ollama serve" to chat with your ghost...'
              : placeholder || 'Ask the ghost a command question, or choose a quick action above...'
          }
          rows={1}
          disabled={isLoading}
          aria-label="Terminal input prompt"
        />

        <button
          type="submit"
          className="send-button"
          disabled={isLoading || !input.trim() || !isOllamaConnected}
          title={!isOllamaConnected ? 'Ollama is offline' : 'Send message (Enter)'}
          aria-label="Send message"
        >
          <Send size={15} />
          <span>Send</span>
        </button>
      </form>

      <div className="input-hint-row">
        <span>
          <CornerDownLeft size={10} style={{ display: 'inline', marginRight: '3px' }} />
          Press <strong>Enter</strong> to send, <strong>Shift+Enter</strong> for newline
        </span>
        <span>
          Safe mode: Commands are <strong>never executed</strong>
        </span>
      </div>
    </div>
  );
}
