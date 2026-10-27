"""Ollama asynchronous HTTP client and integration service."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx

from app.config import settings
from app.schemas.chat import ChatMessageInput, ChatMode, ChatResponse
from app.schemas.ollama import ModelInfo, OllamaModelsResponse, OllamaStatusResponse
from app.services.prompt_templates import get_system_prompt

logger = logging.getLogger("ghostshell.ollama")


class OllamaService:
    """Service to interact with the local Ollama API."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout or settings.ollama_timeout_seconds
        self.default_model = settings.ollama_model

    def _client(self) -> httpx.AsyncClient:
        """Create an async httpx client with standard timeouts."""
        return httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(self.timeout, connect=5.0),
        )

    async def check_status(self) -> OllamaStatusResponse:
        """Check whether the local Ollama daemon is reachable and retrieve version."""
        try:
            async with self._client() as client:
                response = await client.get("/api/version")
                if response.status_code == 200:
                    data = response.json()
                    version = data.get("version", "unknown")
                    return OllamaStatusResponse(
                        connected=True,
                        base_url=self.base_url,
                        version=version,
                        default_model=self.default_model,
                    )
                else:
                    return OllamaStatusResponse(
                        connected=False,
                        base_url=self.base_url,
                        default_model=self.default_model,
                        error=f"Ollama returned HTTP status {response.status_code}",
                        troubleshooting="Check Ollama logs or restart with 'ollama serve'.",
                    )
        except httpx.ConnectError:
            return OllamaStatusResponse(
                connected=False,
                base_url=self.base_url,
                default_model=self.default_model,
                error="Cannot connect to Ollama daemon (Connection Refused).",
                troubleshooting="Make sure Ollama is installed and running. Start it with 'ollama serve' in your terminal.",
            )
        except httpx.TimeoutException:
            return OllamaStatusResponse(
                connected=False,
                base_url=self.base_url,
                default_model=self.default_model,
                error="Timed out attempting to reach Ollama.",
                troubleshooting="Ollama may be busy loading a large model or unresponsive. Verify with 'ollama list'.",
            )
        except Exception as exc:
            logger.warning("Unexpected error during Ollama health check: %s", exc)
            return OllamaStatusResponse(
                connected=False,
                base_url=self.base_url,
                default_model=self.default_model,
                error=f"Unexpected connection error: {str(exc)}",
                troubleshooting="Ensure the OLLAMA_BASE_URL is correct and Ollama is functioning properly.",
            )

    async def list_models(self) -> OllamaModelsResponse:
        """Retrieve the list of models currently pulled and available in Ollama."""
        try:
            async with self._client() as client:
                response = await client.get("/api/tags")
                if response.status_code != 200:
                    return OllamaModelsResponse(
                        connected=False,
                        models=[],
                        default_model=self.default_model,
                        error=f"Failed to fetch models: HTTP {response.status_code}",
                    )

                data = response.json()
                raw_models = data.get("models", [])
                parsed_models: List[ModelInfo] = []

                for m in raw_models:
                    if isinstance(m, dict) and "name" in m:
                        details = m.get("details", {})
                        parsed_models.append(
                            ModelInfo(
                                name=m["name"],
                                modified_at=m.get("modified_at"),
                                size=m.get("size"),
                                parameter_size=details.get("parameter_size") if isinstance(details, dict) else None,
                                family=details.get("family") if isinstance(details, dict) else None,
                            )
                        )

                return OllamaModelsResponse(
                    connected=True,
                    models=parsed_models,
                    default_model=self.default_model,
                )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            return OllamaModelsResponse(
                connected=False,
                models=[],
                default_model=self.default_model,
                error=f"Ollama unreachable: {str(exc)}",
            )
        except Exception as exc:
            logger.warning("Error parsing Ollama models: %s", exc)
            return OllamaModelsResponse(
                connected=False,
                models=[],
                default_model=self.default_model,
                error=f"Malformed or unexpected response from Ollama: {str(exc)}",
            )

    def _build_payload(
        self,
        message: str,
        mode: ChatMode = "general",
        history: Optional[List[ChatMessageInput]] = None,
        model: Optional[str] = None,
        stream: bool = False,
    ) -> tuple[str, Dict[str, Any]]:
        """Construct the Ollama chat payload with guardrail prompts."""
        target_model = model or self.default_model
        system_prompt = get_system_prompt(mode)

        ollama_messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        if history:
            for item in history:
                ollama_messages.append({"role": item.role, "content": item.content})

        ollama_messages.append({"role": "user", "content": message})

        payload = {
            "model": target_model,
            "messages": ollama_messages,
            "stream": stream,
            "options": {
                "temperature": 0.2 if mode != "general" else 0.7,
                "num_ctx": settings.ollama_num_ctx,
                "num_predict": settings.ollama_num_predict,
                "top_p": 0.9,
            },
        }

        return target_model, payload

    async def generate_chat(
        self,
        message: str,
        mode: ChatMode = "general",
        history: Optional[List[ChatMessageInput]] = None,
        model: Optional[str] = None,
    ) -> ChatResponse:
        """Send chat messages to Ollama and return formatted response (atomic)."""
        target_model, payload = self._build_payload(message, mode, history, model, stream=False)

        try:
            async with self._client() as client:
                response = await client.post("/api/chat", json=payload)

                if response.status_code == 404:
                    raise OllamaModelNotFoundError(
                        f"Model '{target_model}' was not found in your local Ollama library. "
                        f"Download it using: 'ollama pull {target_model}'"
                    )

                if response.status_code != 200:
                    err_text = response.text
                    raise OllamaUpstreamError(
                        f"Ollama returned HTTP {response.status_code}: {err_text}"
                    )

                data = response.json()
                msg = data.get("message", {})
                content = msg.get("content", "")

                return ChatResponse(
                    content=content,
                    model=target_model,
                    mode=mode,
                    created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
                    tokens_evaluated=data.get("prompt_eval_count"),
                    tokens_generated=data.get("eval_count"),
                )

        except httpx.ConnectError:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running ('ollama serve')."
            )
        except httpx.TimeoutException:
            raise OllamaTimeoutError(
                f"Ollama request timed out after {self.timeout}s while generating response with model '{target_model}'."
            )

    async def stream_chat(
        self,
        message: str,
        mode: ChatMode = "general",
        history: Optional[List[ChatMessageInput]] = None,
        model: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat tokens progressively from Ollama."""
        target_model, payload = self._build_payload(message, mode, history, model, stream=True)

        try:
            async with self._client() as client:
                async with client.stream("POST", "/api/chat", json=payload) as response:
                    if response.status_code == 404:
                        raise OllamaModelNotFoundError(
                            f"Model '{target_model}' was not found in your local Ollama library. "
                            f"Download it using: 'ollama pull {target_model}'"
                        )
                    if response.status_code != 200:
                        err_text = (await response.aread()).decode("utf-8", errors="ignore")
                        raise OllamaUpstreamError(
                            f"Ollama returned HTTP {response.status_code}: {err_text}"
                        )

                    async for line in response.aiter_lines():
                        trimmed = line.strip()
                        if not trimmed:
                            continue
                        try:
                            data = json.loads(trimmed)
                        except json.JSONDecodeError:
                            continue

                        msg = data.get("message", {})
                        content = msg.get("content", "")
                        is_done = data.get("done", False)

                        yield {
                            "content": content,
                            "done": is_done,
                            "model": target_model,
                            "mode": mode,
                            "created_at": data.get("created_at"),
                            "tokens_evaluated": data.get("prompt_eval_count"),
                            "tokens_generated": data.get("eval_count"),
                        }
        except httpx.ConnectError:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running ('ollama serve')."
            )
        except httpx.TimeoutException:
            raise OllamaTimeoutError(
                f"Ollama stream request timed out after {self.timeout}s with model '{target_model}'."
            )


class OllamaServiceException(Exception):
    """Base exception for Ollama interactions."""
    pass


class OllamaConnectionError(OllamaServiceException):
    """Raised when Ollama cannot be connected to."""
    pass


class OllamaTimeoutError(OllamaServiceException):
    """Raised when Ollama generation times out."""
    pass


class OllamaModelNotFoundError(OllamaServiceException):
    """Raised when the specified model is not downloaded in Ollama."""
    pass


class OllamaUpstreamError(OllamaServiceException):
    """Raised when Ollama returns an HTTP error code."""
    pass


# Default singleton instance
ollama_service = OllamaService()
