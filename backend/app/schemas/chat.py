"""Pydantic schemas for chat endpoints."""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator


ChatMode = Literal["general", "command_oracle", "error_exorcist", "safer_fix"]


class ChatMessageInput(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(..., description="Role of the message author")
    content: str = Field(..., min_length=1, max_length=12000, description="Message text content")

    @field_validator("content")
    @classmethod
    def validate_content_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Message content cannot be empty or pure whitespace")
        return value


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=12000,
        description="The prompt, terminal command, or error log to analyze",
    )
    mode: ChatMode = Field(
        default="general",
        description="GhostShell mode: general, command_oracle, error_exorcist, safer_fix",
    )
    history: List[ChatMessageInput] = Field(
        default_factory=list,
        max_length=20,
        description="Recent conversation history (capped at 20 messages)",
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional override for target Ollama model name",
    )

    @field_validator("message")
    @classmethod
    def validate_message_not_empty(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Message cannot be empty or pure whitespace")
        return value


class ChatResponse(BaseModel):
    content: str = Field(..., description="Assistant response text from local model")
    model: str = Field(..., description="Name of the model that generated this response")
    mode: ChatMode = Field(..., description="Mode applied for this interaction")
    created_at: str = Field(..., description="ISO 8601 generation timestamp")
    tokens_evaluated: Optional[int] = Field(None, description="Prompt evaluation token count")
    tokens_generated: Optional[int] = Field(None, description="Generated token count")
