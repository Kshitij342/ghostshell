import React, { useState } from 'react';
import { Copy, Check, Terminal, ShieldAlert, Sparkles, Bot, User } from 'lucide-react';
import GhostAvatar from './GhostAvatar';

/**
 * Format markdown text safely into React elements without dangerous HTML injection.
 * Gracefully handles incomplete markdown during live token streaming.
 */
function FormattedContent({ text, isStreaming }) {
  if (!text) return null;

  const parts = [];
  const codeBlockRegex = /```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g;
  let lastIndex = 0;
  let match;

  while ((match = codeBlockRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: text.substring(lastIndex, match.index),
      });
    }

    parts.push({
      type: 'code',
      language: match[1] || 'bash',
      content: match[2].trimEnd(),
    });

    lastIndex = match.index + match[0].length;
  }

  // Handle trailing text or incomplete/open code block during streaming
  if (lastIndex < text.length) {
    const remaining = text.substring(lastIndex);
    const openBlockMatch = remaining.match(/^```([a-zA-Z0-9_-]*)\n([\s\S]*)$/);

    if (openBlockMatch) {
      parts.push({
        type: 'code',
        language: openBlockMatch[1] || 'bash',
        content: openBlockMatch[2],
        isOpen: true,
      });
    } else {
      parts.push({
        type: 'text',
        content: remaining,
      });
    }
  }

  return (
    <div className="markdown-body">
      {parts.map((part, idx) => {
        const isLastPart = idx === parts.length - 1;
        if (part.type === 'code') {
          return (
            <CodeBlock
              key={idx}
              language={part.language}
              code={part.content}
              showCursor={isStreaming && isLastPart}
            />
          );
        }
        return (
          <TextParagraphs
            key={idx}
            text={part.content}
            showCursor={isStreaming && isLastPart}
          />
        );
      })}
    </div>
  );
}

function CodeBlock({ language, code, showCursor }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        <span>{language}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="icon-button"
          title="Copy snippet"
          aria-label="Copy snippet"
          style={{ padding: '0.15rem 0.4rem', fontSize: '0.7rem' }}
        >
          {copied ? <Check size={12} color="#00ff9d" /> : <Copy size={12} />}
          <span style={{ marginLeft: '0.25rem' }}>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <pre>
        <code>
          {code}
          {showCursor && <span className="streaming-cursor" aria-hidden="true" />}
        </code>
      </pre>
    </div>
  );
}

function TextParagraphs({ text, showCursor }) {
  const lines = text.split('\n');
  const elements = [];
  let currentList = [];

  const flushList = () => {
    if (currentList.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`}>
          {currentList.map((item, i) => (
            <li key={i}>{renderInline(item)}</li>
          ))}
        </ul>
      );
      currentList = [];
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    const isLastLine = i === lines.length - 1;

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      currentList.push(trimmed.substring(2));
      continue;
    }

    flushList();

    if (!trimmed && !isLastLine) {
      continue;
    }

    const cursorElement = showCursor && isLastLine ? (
      <span className="streaming-cursor" aria-hidden="true" />
    ) : null;

    if (trimmed.startsWith('### ')) {
      elements.push(
        <h4 key={`h4-${i}`}>
          {renderInline(trimmed.substring(4))}
          {cursorElement}
        </h4>
      );
    } else if (trimmed.startsWith('## ')) {
      elements.push(
        <h3 key={`h3-${i}`}>
          {renderInline(trimmed.substring(3))}
          {cursorElement}
        </h3>
      );
    } else if (trimmed.startsWith('# ')) {
      elements.push(
        <h2 key={`h2-${i}`}>
          {renderInline(trimmed.substring(2))}
          {cursorElement}
        </h2>
      );
    } else {
      elements.push(
        <p key={`p-${i}`}>
          {renderInline(line)}
          {cursorElement}
        </p>
      );
    }
  }

  flushList();
  return <>{elements}</>;
}

function renderInline(text) {
  const tokens = [];
  const regex = /(`[^`]+`|\*\*[^*]+\*\*)/g;
  let lastIdx = 0;
  let m;

  while ((m = regex.exec(text)) !== null) {
    if (m.index > lastIdx) {
      tokens.push(text.substring(lastIdx, m.index));
    }
    const matchStr = m[0];
    if (matchStr.startsWith('`') && matchStr.endsWith('`')) {
      tokens.push(
        <code key={`code-${m.index}`}>{matchStr.slice(1, -1)}</code>
      );
    } else if (matchStr.startsWith('**') && matchStr.endsWith('**')) {
      tokens.push(
        <strong key={`bold-${m.index}`}>{matchStr.slice(2, -2)}</strong>
      );
    }
    lastIdx = m.index + matchStr.length;
  }

  if (lastIdx < text.length) {
    tokens.push(text.substring(lastIdx));
  }

  return tokens.length > 0 ? tokens : text;
}

export default function ChatMessage({ message }) {
  const [copiedFull, setCopiedFull] = useState(false);
  const isUser = message.role === 'user';

  const handleCopyFull = () => {
    navigator.clipboard.writeText(message.content);
    setCopiedFull(true);
    setTimeout(() => setCopiedFull(false), 2000);
  };

  const getModeIcon = (mode) => {
    switch (mode) {
      case 'command_oracle':
        return <Terminal size={11} />;
      case 'error_exorcist':
        return <ShieldAlert size={11} />;
      case 'safer_fix':
        return <Sparkles size={11} />;
      default:
        return <Bot size={11} />;
    }
  };

  return (
    <div className={`message-row ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && <GhostAvatar size={28} glowing={true} />}

      <div className="message-bubble">
        <div className="message-meta">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            {isUser ? (
              <>
                <User size={12} />
                <span>developer</span>
              </>
            ) : (
              <>
                <span>GhostShell</span>
                {message.mode && (
                  <span className={`mode-badge ${message.mode}`}>
                    {getModeIcon(message.mode)} {message.mode.replace('_', ' ')}
                  </span>
                )}
                {message.model && (
                  <span style={{ color: '#38bdf8', fontSize: '0.7rem' }}>
                    [{message.model}]
                  </span>
                )}
                {message.isStreaming && (
                  <span style={{ color: '#00ff9d', fontSize: '0.68rem', fontStyle: 'italic' }}>
                    streaming...
                  </span>
                )}
              </>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
            {message.tokens_generated && (
              <span title="Tokens generated">
                {message.tokens_generated} tokens
              </span>
            )}
            <button
              type="button"
              onClick={handleCopyFull}
              className="icon-button"
              title="Copy entire message"
              aria-label="Copy entire message"
            >
              {copiedFull ? <Check size={12} color="#00ff9d" /> : <Copy size={12} />}
            </button>
          </div>
        </div>

        {isUser ? (
          <div style={{ whiteSpace: 'pre-wrap' }}>{message.content}</div>
        ) : (
          <FormattedContent text={message.content} isStreaming={message.isStreaming} />
        )}
      </div>
    </div>
  );
}
