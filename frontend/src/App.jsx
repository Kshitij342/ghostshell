import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import StatusBar from './components/StatusBar';
import QuickActions from './components/QuickActions';
import ChatWindow from './components/ChatWindow';
import ChatInput from './components/ChatInput';
import Footer from './components/Footer';
import { getHealth, getOllamaStatus, getOllamaModels, sendChatMessage } from './services/api';

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
          // If selectedModel is not in list, select first available
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
    setMessages([]);
  };

  // Send message to backend
  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMsg = {
      role: 'user',
      content: trimmed,
      mode: activeMode,
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendChatMessage({
        message: trimmed,
        mode: activeMode,
        history: messages.map((m) => ({ role: m.role, content: m.content })),
        model: selectedModel,
      });

      const assistantMsg = {
        role: 'assistant',
        content: response.content,
        mode: response.mode || activeMode,
        model: response.model,
        tokens_generated: response.tokens_generated,
        created_at: response.created_at,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorContent = `### ⚠️ Spectral Disturbance (${err.type || 'Error'})
${err.message}

${err.resolution ? `**Resolution Steps:**\n${err.resolution}` : ''}
`;

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: errorContent,
          mode: activeMode,
          isError: true,
        },
      ]);
    } finally {
      setIsLoading(false);
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
