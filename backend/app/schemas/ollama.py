"""Pydantic schemas for Ollama service status and models."""

from typing import List, Optional
from pydantic import BaseModel, Field


class ModelInfo(BaseModel):
    name: str = Field(..., description="Model name or tag, e.g. qwen2.5:3b")
    modified_at: Optional[str] = Field(None, description="Last modification timestamp")
    size: Optional[int] = Field(None, description="Size in bytes")
    parameter_size: Optional[str] = Field(None, description="Model parameter size, e.g. 3B")
    family: Optional[str] = Field(None, description="Model family, e.g. qwen2")


class OllamaStatusResponse(BaseModel):
    connected: bool = Field(..., description="Whether Ollama daemon is reachable")
    base_url: str = Field(..., description="Configured Ollama base URL")
    version: Optional[str] = Field(None, description="Ollama server version if available")
    default_model: str = Field(..., description="Configured default model")
    error: Optional[str] = Field(None, description="Error summary if disconnected")
    troubleshooting: Optional[str] = Field(None, description="Actionable help to start Ollama")


class OllamaModelsResponse(BaseModel):
    connected: bool = Field(..., description="Whether Ollama daemon is reachable")
    models: List[ModelInfo] = Field(default_factory=list, description="List of locally installed models")
    default_model: str = Field(..., description="Configured default model")
    error: Optional[str] = Field(None, description="Error message if failed")
