"""Chat endpoint routing and processing for GhostShell (standard & real-time streaming)."""

import json
import logging
from typing import AsyncGenerator
from datetime import datetime, timezone
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
    DETERMINISTIC_GIT_RM_FULL_EXPLANATION,
    get_deterministic_git_rm_response,
    get_deterministic_safety_notice,
    has_contradiction,
    is_exact_git_rm_preview,
    is_incorrect_explanation,
    verify_and_patch_contradictions,
)

logger = logging.getLogger("ghostshell.chat")
router = APIRouter(prefix="/api", tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def post_chat(request: ChatRequest):
    """Process a chat, command explanation, error diagnosis, or safer fix request (atomic)."""
    # Exact dangerous command `git rm -- preview`: return verified explanation directly
    # without calling Ollama or appending any model-generated explanation.
    if is_exact_git_rm_preview(request.message):
        resp_text = get_deterministic_git_rm_response()
        return ChatResponse(
            content=resp_text,
            model=request.model or ollama_service.default_model,
            mode=request.mode,
            created_at=datetime.now(timezone.utc).isoformat(),
            tokens_evaluated=0,
            tokens_generated=len(resp_text.split()),
        )

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
    """Stream chat response tokens progressively via Server-Sent Events (SSE).

    Safety guarantee for guarded queries (e.g. ``git rm -- preview``):
    - For the exact input `git rm -- preview`, the verified explanation is returned
      directly as a clean stream; no model-generated explanation is appended or streamed.
    - For other queries triggering the safety guard, model chunks are buffered and
      suppressed if any contradictory or invalid claims are detected.
    """
    target_model = request.model or ollama_service.default_model

    # Exact dangerous command `git rm -- preview`: stream verified explanation directly.
    # No model inference is performed, preventing any model-generated explanation from appearing.
    if is_exact_git_rm_preview(request.message):
        async def direct_stream_generator() -> AsyncGenerator[str, None]:
            resp_text = get_deterministic_git_rm_response()
            chunk_event = {
                "content": resp_text,
                "done": False,
                "model": target_model,
                "mode": request.mode,
            }
            yield f"data: {json.dumps(chunk_event)}\n\n"
            done_event = {
                "content": "",
                "done": True,
                "model": target_model,
                "mode": request.mode,
                "tokens_generated": len(resp_text.split()),
            }
            yield f"data: {json.dumps(done_event)}\n\n"

        return StreamingResponse(
            direct_stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    safety_notice = get_deterministic_safety_notice(request.message, request.mode)

    async def event_generator() -> AsyncGenerator[str, None]:
        # --- Step 1: emit the grounded safety notice before any model text ---
        if safety_notice:
            preface_event = {
                "content": f"{safety_notice}\n\n",
                "done": False,
                "model": target_model,
                "mode": request.mode,
            }
            yield f"data: {json.dumps(preface_event)}\n\n"

        # --- Step 2: collect the full model response without forwarding it ---
        accumulated_chunks: list[str] = []
        final_done_chunk: dict = {}

        try:
            async for chunk in ollama_service.stream_chat(
                message=request.message,
                mode=request.mode,
                history=request.history,
                model=request.model,
            ):
                if safety_notice:
                    # Buffer; do NOT yield model chunks to the client yet.
                    if chunk.get("content"):
                        accumulated_chunks.append(chunk["content"])
                    if chunk.get("done"):
                        final_done_chunk = chunk
                else:
                    # No safety guard active — stream normally.
                    yield f"data: {json.dumps(chunk)}\n\n"

        except OllamaModelNotFoundError as exc:
            err_data = {
                "error": "Model Not Found",
                "message": str(exc),
                "resolution": f"Run 'ollama pull {request.model or ollama_service.default_model}' in your terminal.",
                "done": True,
            }
            yield f"data: {json.dumps(err_data)}\n\n"
            return
        except OllamaConnectionError as exc:
            err_data = {
                "error": "Ollama Unavailable",
                "message": str(exc),
                "resolution": "Start the local Ollama daemon by running 'ollama serve' in your terminal.",
                "done": True,
            }
            yield f"data: {json.dumps(err_data)}\n\n"
            return
        except OllamaTimeoutError as exc:
            err_data = {
                "error": "Ollama Timeout",
                "message": str(exc),
                "resolution": "The model took too long to generate. Consider using a smaller model.",
                "done": True,
            }
            yield f"data: {json.dumps(err_data)}\n\n"
            return
        except OllamaUpstreamError as exc:
            err_data = {
                "error": "Ollama Upstream Error",
                "message": str(exc),
                "resolution": "Check Ollama process and logs.",
                "done": True,
            }
            yield f"data: {json.dumps(err_data)}\n\n"
            return
        except Exception as exc:
            logger.exception("Stream error: %s", exc)
            err_data = {
                "error": "Internal Stream Error",
                "message": str(exc),
                "done": True,
            }
            yield f"data: {json.dumps(err_data)}\n\n"
            return

        # --- Step 3: resolve buffered model text (only reached when safety_notice is set) ---
        if safety_notice:
            full_model_text = "".join(accumulated_chunks)

            if is_incorrect_explanation(full_model_text):
                # Contradictory / incorrect model text is discarded; emit the deterministic explanation.
                explanation_event = {
                    "content": DETERMINISTIC_GIT_RM_FULL_EXPLANATION,
                    "done": False,
                    "model": target_model,
                    "mode": request.mode,
                }
                yield f"data: {json.dumps(explanation_event)}\n\n"
            else:
                # Model text is verified safe — forward it as a single content chunk.
                if full_model_text:
                    safe_content_event = {
                        "content": full_model_text,
                        "done": False,
                        "model": target_model,
                        "mode": request.mode,
                    }
                    yield f"data: {json.dumps(safe_content_event)}\n\n"

            # Emit the terminal done chunk (without content).
            done_event = {**final_done_chunk, "content": ""}
            yield f"data: {json.dumps(done_event)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
