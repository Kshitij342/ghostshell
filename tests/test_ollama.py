"""Tests for Ollama connectivity and model discovery endpoints."""

from unittest.mock import AsyncMock, patch
import httpx
from app.schemas.ollama import OllamaModelsResponse, OllamaStatusResponse


def test_ollama_status_connected(client):
    """Test /api/ollama/status when Ollama is reachable."""
    mock_status = OllamaStatusResponse(
        connected=True,
        base_url="http://127.0.0.1:11434",
        version="0.3.12",
        default_model="qwen2.5:3b",
    )
    with patch("app.routes.ollama.ollama_service.check_status", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_status
        response = client.get("/api/ollama/status")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert data["version"] == "0.3.12"
        assert data["default_model"] == "qwen2.5:3b"


def test_ollama_status_unavailable_controlled(client):
    """Test /api/ollama/status when Ollama is unavailable returns a controlled response without crashing."""
    mock_status = OllamaStatusResponse(
        connected=False,
        base_url="http://127.0.0.1:11434",
        default_model="qwen2.5:3b",
        error="Cannot connect to Ollama daemon (Connection Refused).",
        troubleshooting="Make sure Ollama is installed and running.",
    )
    with patch("app.routes.ollama.ollama_service.check_status", new_callable=AsyncMock) as mock_check:
        mock_check.return_value = mock_status
        response = client.get("/api/ollama/status")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False
        assert "Cannot connect" in data["error"]
        assert "troubleshooting" in data


def test_ollama_models_listing_success(client):
    """Test /api/ollama/models returns parsed model list."""
    mock_models_resp = OllamaModelsResponse(
        connected=True,
        models=[
            {"name": "qwen2.5:3b", "size": 1900000000, "parameter_size": "3B", "family": "qwen2"},
            {"name": "llama3.2:3b", "size": 2000000000, "parameter_size": "3B", "family": "llama"},
        ],
        default_model="qwen2.5:3b",
    )
    with patch("app.routes.ollama.ollama_service.list_models", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_models_resp
        response = client.get("/api/ollama/models")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is True
        assert len(data["models"]) == 2
        assert data["models"][0]["name"] == "qwen2.5:3b"


def test_ollama_models_listing_unavailable(client):
    """Test /api/ollama/models handles unreachable service safely."""
    mock_models_resp = OllamaModelsResponse(
        connected=False,
        models=[],
        default_model="qwen2.5:3b",
        error="Ollama unreachable: Connection refused",
    )
    with patch("app.routes.ollama.ollama_service.list_models", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = mock_models_resp
        response = client.get("/api/ollama/models")
        assert response.status_code == 200
        data = response.json()
        assert data["connected"] is False
        assert data["models"] == []
        assert "unreachable" in data["error"]
