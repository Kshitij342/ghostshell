"""Ollama status and model discovery routes."""

from fastapi import APIRouter
from app.schemas.ollama import OllamaModelsResponse, OllamaStatusResponse
from app.services.ollama_service import ollama_service

router = APIRouter(prefix="/api/ollama", tags=["Ollama"])


@router.get("/status", response_model=OllamaStatusResponse)
async def get_ollama_status():
    """Check connectivity to the local Ollama instance without raising HTTP errors."""
    return await ollama_service.check_status()


@router.get("/models", response_model=OllamaModelsResponse)
async def get_ollama_models():
    """Retrieve locally available models from Ollama."""
    return await ollama_service.list_models()
