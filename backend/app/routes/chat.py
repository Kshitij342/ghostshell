"""Chat endpoint routing and processing for GhostShell (standard & real-time streaming)."""

import json
import logging
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ollama_service import (
    OllamaConnectionError,
    OllamaModelNotFoundError,
    OllamaTimeoutError,
    OllamaUpstreamError,
    ollama_service,
)
from app.services.safety_guard import (
    CONTRADICTION_CORRECTION_BANNER,
    get_deterministic_safety_notice,
    verify_and_patch_contradictions,
)

logger = logging.getLogger("ghostshell.chat")
router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def post_chat(request: ChatRequest):
    """Process a chat, command explanation, error diagnosis, or safer fix request (atomic)."""
    try:
        safety_notice = get_deterministic_safety_notice(request.message, request.mode)

        response = await ollama_service.generate_chat(
            message=request.message,
            mode=request.mode,
            history=request.history,
            model=request.model,
        )

        if safety_notice:
            response.content = verify_and_patch_contradictions(safety_notice, response.content)

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


@router.post("/chat/stream")
async def post_chat_stream(request: ChatRequest):
    """Stream chat response tokens progressively via Server-Sent Events (SSE)."""
    safety_notice = get_deterministic_safety_notice(request.message, request.mode)
    target_model = request.model or ollama_service.default_model

    async def event_generator() -> AsyncGenerator[str, None]:
        # Prepend grounded deterministic notice immediately before streaming model output
        if safety_notice:
            preface_event = {
                "content": f"{safety_notice}\n\n",
                "done": False,
                "model": target_model,
                "mode": request.mode,
            }
            yield f"data: {json.dumps(preface_event)}\n\n"

        accumulated_chunks = []
        try:
            async for chunk in ollama_service.stream_chat(
                message=request.message,
                mode=request.mode,
                history=request.history,
                model=request.model,
            ):
                if chunk.get("content"):
                    accumulated_chunks.append(chunk["content"])

                # If the stream is finishing, check if the accumulated model text contradicted the safety notice
                if chunk.get("done") and safety_notice:
                    full_model_text = "".join(accumulated_chunks).lower()
                    contradiction_patterns = [
                        r"previews?\s+(the\s+)?deletion",
                        r"activates?\s+(a\s+)?preview",
                        r"preview\s+mode",
                        r"only\s+modifies?\s+(the\s+)?index",
                        r"only\s+removes?\s+from\s+(the\s+)?index",
                        r"safe\s+to\s+(run|execute)\s+git\s+rm\s+--\s+preview",
                    ]
                    import re
                    if any(re.search(pat, full_model_text) for pat in contradiction_patterns):
                        corr_event = {
                            "content": CONTRADICTION_CORRECTION_BANNER,
                            "done": False,
                            "model": target_model,
                            "mode": request.mode,
                        }
                        yield f"data: {json.dumps(corr_event)}\n\n"

                payload_str = json.dumps(chunk)
                yield f"data: {payload_str}\n\n"
        except OllamaModelNotFoundError as exc:

            err_data = {
                "error": "Model Not Found",
                "message": str(exc),
                "resolution": f"Run 'ollama pull {request.model or ollama_service.default_model}' in your terminal.",
                "done": True,
            }
            yield f"data: {json.dumps(err_data)}\n\n"
        except OllamaConnectionError as exc:
            err_data = {
                "error": "Ollama Unavailable",
                "message": str(exc),
                "resolution": "Start the local Ollama daemon by running 'ollama serve' in your terminal.",
                "done": True,
            }
            yield f"data: {json.dumps(err_data)}\n\n"
        except OllamaTimeoutError as exc:
            err_data = {
                "error": "Ollama Timeout",
                "message": str(exc),
                "resolution": "The model took too long to generate. Consider using a smaller model.",
                "done": True,
            }
            yield f"data: {json.dumps(err_data)}\n\n"
        except OllamaUpstreamError as exc:
            err_data = {
                "error": "Ollama Upstream Error",
                "message": str(exc),
                "resolution": "Check Ollama process and logs.",
                "done": True,
            }
            yield f"data: {json.dumps(err_data)}\n\n"
        except Exception as exc:
            logger.exception("Stream error: %s", exc)
            err_data = {
                "error": "Internal Stream Error",
                "message": str(exc),
                "done": True,
            }
            yield f"data: {json.dumps(err_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
