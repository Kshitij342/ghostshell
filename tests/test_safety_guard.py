"""Tests for GhostShell deterministic safety guard layer."""

import json
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
import pytest
from app.schemas.chat import ChatResponse
from app.services.safety_guard import (
    DETERMINISTIC_GIT_RM_PREVIEW_NOTICE,
    CONTRADICTION_CORRECTION_BANNER,
    get_deterministic_safety_notice,
    verify_and_patch_contradictions,
)


def test_deterministic_git_rm_preview_detection():
    """Verify that only relevant git rm / separator / preview queries trigger the safety notice."""
    # Positive triggers
    assert get_deterministic_safety_notice("git rm -- preview", "safer_fix") is not None
    assert get_deterministic_safety_notice("Is git rm -- preview safe to run?", "safer_fix") is not None
    assert get_deterministic_safety_notice("explain: git rm -- preview", "command_oracle") is not None
    assert get_deterministic_safety_notice("will git rm -- file preview deletion?", "safer_fix") is not None

    # Negative triggers (must NOT intercept ordinary or unrelated chat)
    assert get_deterministic_safety_notice("git status", "general") is None
    assert get_deterministic_safety_notice("git rm file.txt", "general") is None
    assert get_deterministic_safety_notice("ModuleNotFoundError: No module named 'requests'", "error_exorcist") is None
    assert get_deterministic_safety_notice("docker build -t app .", "command_oracle") is None
    assert get_deterministic_safety_notice("find . -name '*.log' -delete", "safer_fix") is None


def test_deterministic_notice_content_accuracy():
    """Verify that the safety notice covers all four required factual elements."""
    notice = DETERMINISTIC_GIT_RM_PREVIEW_NOTICE

    # 1. `--` separates options from path arguments; does not enable preview
    assert "separates command-line options from path arguments" in notice
    assert "enable preview" in notice.lower()
    assert "argument separator" in notice.lower()

    # 2. `git rm -- preview` treats preview as a path argument
    assert "treats `preview` strictly as a path argument" in notice


    # 3. `git rm` normally removes tracked paths from working tree and stages removal
    assert "working tree" in notice
    assert "stages their removal" in notice or "removes tracked paths" in notice
    assert "not merely modify the index" in notice.lower() or "working tree and the index" in notice

    # 4. Read-only inspection recommendations
    assert "git status --short" in notice
    assert "git ls-files" in notice
    assert "git ls-files -- path/to/file" in notice


def test_verify_and_patch_contradictions_with_hallucinating_model():
    """Verify that hallucinated model text is overridden with an explicit correction banner."""
    notice = DETERMINISTIC_GIT_RM_PREVIEW_NOTICE
    hallucinated_model_content = (
        "Running `git rm -- preview` activates preview mode and previews the deletion. "
        "It only modifies the index and is safe to execute."
    )

    patched = verify_and_patch_contradictions(notice, hallucinated_model_content)

    assert patched.startswith(notice)
    assert "Safety Override" in patched
    assert "will delete the file or directory named 'preview'" in patched


def test_chat_endpoint_deterministic_safety_layer(client):
    """Test that POST /api/chat prepends deterministic notice and corrects contradictions."""
    hallucinated_resp = ChatResponse(
        content="`git rm -- preview` previews the deletion. It only modifies the index.",
        model="llama3.2:1b",
        mode="safer_fix",
        created_at=datetime.now(timezone.utc).isoformat(),
        tokens_evaluated=100,
        tokens_generated=50,
    )

    with patch("app.routes.chat.ollama_service.generate_chat", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = hallucinated_resp
        response = client.post(
            "/api/chat",
            json={
                "message": "Is git rm -- preview safe to test?",
                "mode": "safer_fix",
                "model": "llama3.2:1b",
            },
        )
        assert response.status_code == 200
        data = response.json()
        content = data["content"]

        # Notice must be prepended
        assert "Deterministic Safety Notice: `git rm` & `--` Argument Semantics" in content
        assert "git status --short" in content
        # Correction banner must be appended due to model hallucination
        assert "Safety Override" in content


def test_chat_stream_endpoint_deterministic_safety_layer(client):
    """Test that POST /api/chat/stream yields deterministic preface and correction banner."""
    async def mock_hallucinating_stream(*args, **kwargs):
        yield {"content": "`git rm -- preview` activates ", "done": False, "model": "llama3.2:1b"}
        yield {"content": "preview mode and only modifies the index.", "done": False, "model": "llama3.2:1b"}
        yield {"content": "", "done": True, "model": "llama3.2:1b", "tokens_generated": 20}

    with patch("app.routes.chat.ollama_service.stream_chat", side_effect=mock_hallucinating_stream):
        response = client.post(
            "/api/chat/stream",
            json={
                "message": "How do I use git rm -- preview?",
                "mode": "safer_fix",
                "model": "llama3.2:1b",
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        lines = [line.strip() for line in response.text.split("\n") if line.startswith("data: ")]

        # Chunk 1: Deterministic safety preface
        chunk1 = json.loads(lines[0][6:])
        assert "Deterministic Safety Notice: `git rm` & `--` Argument Semantics" in chunk1["content"]
        assert "git status --short" in chunk1["content"]

        # Final chunks must include correction banner due to model contradiction
        all_text = "".join(json.loads(line[6:])["content"] for line in lines)
        assert "Safety Override" in all_text
