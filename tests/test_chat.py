"""Tests for the GhostShell chat, command explanation, error diagnosis, and streaming endpoints."""

import json
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


def test_chat_success_error_exorcist_requests_diagnosis(client):
    """Test that Error Exorcist structured diagnosis for missing module is processed."""
    mock_diagnosis = (
        "### 1. Error Summary\n"
        "Python cannot locate the 'requests' library in the active environment.\n\n"
        "### 2. Most Likely Cause\n"
        "The package is not installed in the currently active Python interpreter.\n\n"
        "### 5. Recommended Fix\n"
        "`python -m pip install requests`"
    )
    mock_resp = ChatResponse(
        content=mock_diagnosis,
        model="qwen2.5:3b",
        mode="error_exorcist",
        created_at=datetime.now(timezone.utc).isoformat(),
        tokens_evaluated=150,
        tokens_generated=95,
    )
    with patch("app.routes.chat.ollama_service.generate_chat", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_resp
        response = client.post(
            "/api/chat",
            json={
                "message": "ModuleNotFoundError: No module named 'requests'",
                "mode": "error_exorcist",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "Error Summary" in data["content"]
        assert "python -m pip install requests" in data["content"]
        assert data["mode"] == "error_exorcist"


def test_chat_success_safer_fix_read_only_inspection(client):
    """Test Safer Fix structured response warns about destructive git rm and recommends read-only inspection."""
    mock_safer = (
        "### 1. Identified Risk\n"
        "`git rm` deletes tracked files from the working tree and index. The argument `--` does not preview changes; "
        "it separates options from paths, treating any subsequent string as a target file to delete.\n\n"
        "### 2. Safer Strategy\n"
        "Inspect repository and file status with read-only commands before making destructive changes.\n\n"
        "### 3. Safer Command / Fix\n"
        "Use `git status --short` to inspect working tree status, or `git ls-files` to inspect tracked files safely."
    )
    mock_resp = ChatResponse(
        content=mock_safer,
        model="qwen2.5:3b",
        mode="safer_fix",
        created_at=datetime.now(timezone.utc).isoformat(),
        tokens_evaluated=130,
        tokens_generated=70,
    )
    with patch("app.routes.chat.ollama_service.generate_chat", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = mock_resp
        response = client.post(
            "/api/chat",
            json={
                "message": "Is git rm -- preview safe to run?",
                "mode": "safer_fix",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "git status --short" in data["content"]
        assert "git ls-files" in data["content"]
        assert data["mode"] == "safer_fix"



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


# =========================================================================
# Streaming Endpoint Tests (/api/chat/stream)
# =========================================================================

def test_chat_stream_progressive_chunks(client):
    """Test that /api/chat/stream yields SSE formatted data events and completes."""
    async def mock_stream_generator(*args, **kwargs):
        yield {"content": "Dissecting ", "done": False, "model": "qwen2.5:3b"}
        yield {"content": "command...", "done": False, "model": "qwen2.5:3b"}
        yield {"content": "", "done": True, "model": "qwen2.5:3b", "tokens_generated": 25}

    with patch("app.routes.chat.ollama_service.stream_chat", side_effect=mock_stream_generator):
        response = client.post(
            "/api/chat/stream",
            json={"message": "ls -la", "mode": "command_oracle"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        lines = [line.strip() for line in response.text.split("\n") if line.startswith("data: ")]
        assert len(lines) == 3

        chunk1 = json.loads(lines[0][6:])
        assert chunk1["content"] == "Dissecting "
        assert chunk1["done"] is False

        chunk2 = json.loads(lines[1][6:])
        assert chunk2["content"] == "command..."

        chunk3 = json.loads(lines[2][6:])
        assert chunk3["done"] is True
        assert chunk3["tokens_generated"] == 25


def test_chat_stream_ollama_unavailable_event(client):
    """Test that /api/chat/stream yields error event when Ollama connection fails."""
    async def mock_failing_generator(*args, **kwargs):
        raise OllamaConnectionError("Cannot connect to Ollama daemon")
        yield  # make it a generator

    with patch("app.routes.chat.ollama_service.stream_chat", side_effect=mock_failing_generator):
        response = client.post(
            "/api/chat/stream",
            json={"message": "test message"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        lines = [line.strip() for line in response.text.split("\n") if line.startswith("data: ")]
        assert len(lines) >= 1
        err_event = json.loads(lines[0][6:])
        assert err_event["error"] == "Ollama Unavailable"
        assert err_event["done"] is True
        assert "ollama serve" in err_event["resolution"]


def test_chat_stream_model_not_found_event(client):
    """Test that /api/chat/stream yields error event when target model is not found."""
    async def mock_missing_model_generator(*args, **kwargs):
        raise OllamaModelNotFoundError("Model 'nonexistent:3b' not found")
        yield

    with patch("app.routes.chat.ollama_service.stream_chat", side_effect=mock_missing_model_generator):
        response = client.post(
            "/api/chat/stream",
            json={"message": "test", "model": "nonexistent:3b"},
        )
        assert response.status_code == 200
        lines = [line.strip() for line in response.text.split("\n") if line.startswith("data: ")]
        assert len(lines) >= 1
        err_event = json.loads(lines[0][6:])
        assert err_event["error"] == "Model Not Found"
        assert "ollama pull" in err_event["resolution"]


def test_chat_stream_timeout_event(client):
    """Test that /api/chat/stream yields error event on inference timeout."""
    async def mock_timeout_generator(*args, **kwargs):
        raise OllamaTimeoutError("Timed out after 60s")
        yield

    with patch("app.routes.chat.ollama_service.stream_chat", side_effect=mock_timeout_generator):
        response = client.post(
            "/api/chat/stream",
            json={"message": "diagnose complex issue"},
        )
        assert response.status_code == 200
        lines = [line.strip() for line in response.text.split("\n") if line.startswith("data: ")]
        assert len(lines) >= 1
        err_event = json.loads(lines[0][6:])
        assert err_event["error"] == "Ollama Timeout"
