"""Chat endpoint routing and processing for GhostShell."""

import logging
from fastapi import APIRouter, HTTPException, status
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ollama_service import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    OllamaUpstreamError,
    ollama_service,
)

logger = logging.getLogger("ghostshell.chat")
router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def post_chat(request: ChatRequest):
    """Process a chat, command explanation, error diagnosis, or safer fix request."""
    try:
        response = await ollama_service.generate_chat(
            message=request.message,
            mode=request.mode,
            history=request.history,
            model=request.model,
        )
        return response

    except OllamaModelNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "Model Not Found",
                "message": str(exc),
                "resolution": f"Run 'ollama pull {request.model or ollama_service.default_model}' in your terminal.",
            },
        )

    except OllamaConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Ollama Unavailable",
                "message": str(exc),
                "resolution": "Start the local Ollama daemon by running 'ollama serve' in your terminal.",
            },
        )

    except OllamaTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "error": "Ollama Timeout",
                "message": str(exc),
                "resolution": "The model took too long to generate a response. Consider using a smaller model like qwen2.5:3b.",
            },
        )

    except OllamaUpstreamError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Ollama Upstream Error",
                "message": str(exc),
                "resolution": "Check the local Ollama process and terminal logs.",
            },
        )

    except Exception as exc:
        logger.exception("Unexpected error processing chat request: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal Error",
                "message": f"An unexpected error occurred: {str(exc)}",
                "resolution": "Check backend logs or retry.",
            },
        )
