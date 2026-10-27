"""Tests for the GhostShell chat, command explanation, and error diagnosis endpoint."""

from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
import pytest
from app.schemas.chat import ChatResponse
from app.services.ollama_service import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    OllamaUpstreamError,
)


def test_chat_validation_rejects_empty_message(client):
    """Test that chat endpoint rejects empty message string."""
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_validation_rejects_whitespace_message(client):
    """Test that chat endpoint rejects whitespace-only string."""
    response = client.post("/api/chat", json={"message": "   \n\t  "})
    assert response.status_code == 422


def test_chat_validation_rejects_excessively_long_message(client):
    """Test that chat endpoint rejects messages exceeding length boundary."""
    huge_message = "A" * 12001
    response = client.post("/api/chat", json={"message": huge_message})
    assert response.status_code == 422


def test_chat_success_command_oracle(client):
    """Test successful chat processing in command_oracle mode."""
    mock_resp = ChatResponse(
        content="**Overview**: Recursively removes files forcefully.\n**Risks**: Irreversible loss.",
        model="qwen2.5:3b",
        mode="command_oracle",
        created_at=datetime.now(timezone.utc).isoformat(),
        tokens_evaluated=120,
        tokens_generated=80,
    )
    with patch("app.routes.chat.ollama_service.generate_chat", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_resp
        response = client.post(
            "/api/chat",
            json={
                "message": "rm -rf /tmp/cache",
                "mode": "command_oracle",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "Overview" in data["content"]
        assert data["mode"] == "command_oracle"
        assert data["model"] == "qwen2.5:3b"


def test_chat_ollama_unavailable_returns_503(client):
    """Test that when Ollama is unavailable, the chat endpoint returns 503 with resolution steps."""
    with patch("app.routes.chat.ollama_service.generate_chat", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = OllamaConnectionError("Cannot connect to Ollama at http://127.0.0.1:11434")
        response = client.post(
            "/api/chat",
            json={"message": "How do I list docker containers?"},
        )
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "Ollama Unavailable"
        assert "ollama serve" in data["detail"]["resolution"]


def test_chat_model_not_found_returns_404(client):
    """Test that missing model returns 404 with instructions to pull it."""
    with patch("app.routes.chat.ollama_service.generate_chat", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = OllamaModelNotFoundError("Model 'missing:model' not found")
        response = client.post(
            "/api/chat",
            json={"message": "explain git rebase", "model": "missing:model"},
        )
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["error"] == "Model Not Found"
        assert "ollama pull" in data["detail"]["resolution"]


def test_chat_timeout_returns_504(client):
    """Test that timeout from Ollama returns 504."""
    with patch("app.routes.chat.ollama_service.generate_chat", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = OllamaTimeoutError("Timed out after 60s")
        response = client.post(
            "/api/chat",
            json={"message": "diagnose this error: segfault"},
        )
        assert response.status_code == 504
        data = response.json()
        assert data["detail"]["error"] == "Ollama Timeout"


def test_chat_upstream_error_returns_502(client):
    """Test that upstream error from Ollama returns 502 without crashing."""
    with patch("app.routes.chat.ollama_service.generate_chat", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = OllamaUpstreamError("Ollama returned HTTP 500: Internal error")
        response = client.post(
            "/api/chat",
            json={"message": "test message"},
        )
        assert response.status_code == 502
        data = response.json()
        assert data["detail"]["error"] == "Ollama Upstream Error"
