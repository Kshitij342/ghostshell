import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import StatusBar from './components/StatusBar';
import QuickActions from './components/QuickActions';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import Footer from './components/Footer';
import { getHealth, getOllamaStatus, getOllamaModels, streamChatMessage, appendStreamContent } from './services/api';

export default function App() {
  const [backendStatus, setBackendStatus] = useState(null);
  const [ollamaStatus, setOllamaStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('qwen2.5:3b');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [activeMode, setActiveMode] = useState('general');
  const [placeholder, setPlaceholder] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const abortControllerRef = useRef(null);

  // Check backend health & Ollama connection
  const checkStatus = useCallback(async () => {
    setIsRefreshing(true);
    try {
      // 1. Backend health
      try {
        const health = await getHealth();
        setBackendStatus(health);
      } catch (err) {
        setBackendStatus({ status: 'error', error: err.message });
      }

      // 2. Ollama status
      try {
        const status = await getOllamaStatus();
        setOllamaStatus(status);
        if (status.default_model && !selectedModel) {
          setSelectedModel(status.default_model);
        }
      } catch (err) {
        setOllamaStatus({ connected: false, error: err.message });
      }

      // 3. Ollama models
      try {
        const modelsData = await getOllamaModels();
        if (modelsData.models && modelsData.models.length > 0) {
          setModels(modelsData.models);
          const hasSelected = modelsData.models.some((m) => m.name === selectedModel);
          if (!hasSelected) {
            setSelectedModel(modelsData.models[0].name);
          }
        }
      } catch (err) {
        // Models list may fail if Ollama is down, which is expected
      }
    } finally {
      setIsRefreshing(false);
    }
  }, [selectedModel]);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  // Handle Quick Action mode selection
  const handleSelectMode = (mode, modePlaceholder) => {
    setActiveMode(mode);
    setPlaceholder(modePlaceholder || '');
  };

  const handleResetMode = () => {
    setActiveMode('general');
    setPlaceholder('');
  };

  const handleSampleClick = (mode, text) => {
    setActiveMode(mode);
    setInput(text);
  };

  const handleClearMessages = () => {
    if (!isLoading) {
      setMessages([]);
    }
  };

  // Stop generation cleanly
  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  };

  // Send message to backend with real-time progressive streaming
  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMsg = {
      role: 'user',
      content: trimmed,
      mode: activeMode,
    };

    const initialAssistantMsg = {
      role: 'assistant',
      content: '',
      mode: activeMode,
      model: selectedModel,
      isStreaming: true,
    };

    const historyPayload = messages.map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, userMsg, initialAssistantMsg]);
    setInput('');
    setIsLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let accumulatedContent = '';

    try {
      await streamChatMessage({
        message: trimmed,
        mode: activeMode,
        history: historyPayload,
        model: selectedModel,
        signal: controller.signal,
        onChunk: (chunk) => {
          if (chunk.content) {
            accumulatedContent = appendStreamContent(accumulatedContent, chunk.content);
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  content: accumulatedContent,
                  tokens_generated: chunk.tokens_generated || updated[lastIdx].tokens_generated,
                  model: chunk.model || updated[lastIdx].model,
                };
              }
              return updated;
            });
          }

          if (chunk.done) {
            setMessages((prev) => {
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
                updated[lastIdx] = {
                  ...updated[lastIdx],
                  isStreaming: false,
                  tokens_generated: chunk.tokens_generated || updated[lastIdx].tokens_generated,
                };
              }
              return updated;
            });
          }
        },
      });

      // Ensure final state marks streaming complete
      setMessages((prev) => {
        const updated = [...prev];
        const lastIdx = updated.length - 1;
        if (lastIdx >= 0 && updated[lastIdx].role === 'assistant' && updated[lastIdx].isStreaming) {
          updated[lastIdx] = { ...updated[lastIdx], isStreaming: false };
        }
        return updated;
      });

    } catch (err) {
      if (err.name === 'AbortError') {
        // User clicked Stop
        setMessages((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
            updated[lastIdx] = {
              ...updated[lastIdx],
              content: accumulatedContent
                ? `${accumulatedContent}\n\n*(Generation stopped by user)*`
                : '*(Generation stopped by user)*',
              isStreaming: false,
            };
          }
          return updated;
        });
      } else {
        const errorContent = `### ⚠️ Spectral Disturbance (${err.type || 'Error'})
${err.message}

${err.resolution ? `**Resolution Steps:**\n${err.resolution}` : ''}
`;

        setMessages((prev) => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
            updated[lastIdx] = {
              ...updated[lastIdx],
              content: errorContent,
              isStreaming: false,
              isError: true,
            };
          } else {
            updated.push({
              role: 'assistant',
              content: errorContent,
              mode: activeMode,
              isStreaming: false,
              isError: true,
            });
          }
          return updated;
        });
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="app-container">
      <Header />

      <StatusBar
        backendStatus={backendStatus}
        ollamaStatus={ollamaStatus}
        models={models}
        selectedModel={selectedModel}
        onSelectModel={setSelectedModel}
        onRefresh={checkStatus}
        isRefreshing={isRefreshing}
      />

      <main className="main-content" style={{ marginTop: '1rem' }}>
        <QuickActions
          activeMode={activeMode}
          onSelectMode={handleSelectMode}
        />

        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          ollamaStatus={ollamaStatus}
          onClearMessages={handleClearMessages}
          onSampleClick={handleSampleClick}
        />

        <ChatInput
          input={input}
          setInput={setInput}
          onSend={handleSend}
          onStop={handleStop}
          isLoading={isLoading}
          activeMode={activeMode}
          onResetMode={handleResetMode}
          placeholder={placeholder}
          isOllamaConnected={ollamaStatus?.connected === true}
        />
      </main>

      <Footer />
    </div>
  );
}
