"""Tests for GhostShell deterministic safety guard layer."""

import json
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone
import pytest
from app.schemas.chat import ChatResponse
from app.services.safety_guard import (
    DETERMINISTIC_GIT_RM_PREVIEW_NOTICE,
    DETERMINISTIC_GIT_RM_FULL_EXPLANATION,
    CONTRADICTION_CORRECTION_BANNER,
    get_deterministic_safety_notice,
    has_contradiction,
    is_incorrect_explanation,
    verify_and_patch_contradictions,
)


# ---------------------------------------------------------------------------
# Notice trigger detection
# ---------------------------------------------------------------------------

def test_deterministic_git_rm_preview_detection():
    """Verify that only relevant git rm / separator / preview queries trigger the safety notice."""
    # Positive triggers
    assert get_deterministic_safety_notice("git rm -- preview", "safer_fix") is not None
    assert get_deterministic_safety_notice("git rm -- preview", "general") is not None
    assert get_deterministic_safety_notice("git rm -- preview", "command_oracle") is not None
    assert get_deterministic_safety_notice("Is git rm -- preview safe to run?", "safer_fix") is not None
    assert get_deterministic_safety_notice("explain: git rm -- preview", "command_oracle") is not None
    assert get_deterministic_safety_notice("will git rm -- file preview deletion?", "safer_fix") is not None

    # Negative triggers (must NOT intercept ordinary or unrelated chat)
    assert get_deterministic_safety_notice("git status", "general") is None
    assert get_deterministic_safety_notice("git rm file.txt", "general") is None
    assert get_deterministic_safety_notice("ModuleNotFoundError: No module named 'requests'", "error_exorcist") is None
    assert get_deterministic_safety_notice("docker build -t app .", "command_oracle") is None
    assert get_deterministic_safety_notice("find . -name '*.log' -delete", "safer_fix") is None


# ---------------------------------------------------------------------------
# Notice content accuracy
# ---------------------------------------------------------------------------

def test_deterministic_notice_content_accuracy():
    """Verify that the safety notice covers all required factual elements."""
    notice = DETERMINISTIC_GIT_RM_PREVIEW_NOTICE

    # 1. Preserves exact command and warns against altering or inventing flags
    assert "git rm -- preview" in notice
    assert "git rm --preview" not in notice
    assert "--preview" in notice

    # 2. `--` terminates option parsing; does not mean preview or dry-run
    assert "terminates option parsing" in notice.lower()
    assert "separates command-line options from path arguments" in notice
    assert "preview, confirmation, or dry-run" in notice.lower()

    # 3. `git rm -- preview` treats preview strictly as a path argument
    assert "treats `preview` strictly as a path argument" in notice

    # 4. Destructive removal from working tree and index
    assert "working tree and the index" in notice
    assert "not merely modify the index" in notice.lower()

    # 5. Exact safe dry-run equivalent
    assert "git rm --dry-run -- preview" in notice

    # 6. Read-only inspection recommendations
    assert "git status --short" in notice
    assert "git ls-files" in notice
    assert "git ls-files -- preview" in notice


# ---------------------------------------------------------------------------
# Full explanation content accuracy
# ---------------------------------------------------------------------------

def test_full_explanation_content_accuracy():
    """Verify DETERMINISTIC_GIT_RM_FULL_EXPLANATION covers every required fact."""
    exp = DETERMINISTIC_GIT_RM_FULL_EXPLANATION

    # 1. Preserves exact command
    assert "git rm -- preview" in exp
    assert "git rm --preview" not in exp
    assert "--preview" in exp

    # 2. `--` terminates option parsing
    assert "terminates option parsing" in exp
    assert "does not mean preview or dry-run" in exp

    # 3. `preview` is interpreted as a path argument
    assert "interpreted strictly as a path argument" in exp
    assert "path argument" in exp

    # 4. Destructive removal
    assert "working tree" in exp
    assert "index" in exp

    # 5. Exact safe dry-run equivalent
    assert "git rm --dry-run -- preview" in exp
    assert "--dry-run" in exp

    # 6. Read-only alternatives
    assert "git status --short" in exp
    assert "git ls-files -- preview" in exp

    # 7. No fabricated flags or progress bar
    assert "exclude=" not in exp
    assert "progress" not in exp.lower()


# ---------------------------------------------------------------------------
# is_incorrect_explanation & has_contradiction tests
# ---------------------------------------------------------------------------

def test_is_incorrect_explanation_detects_altered_command():
    """Detects when model alters `git rm -- preview` to `git rm --preview` or invents `--preview`."""
    assert is_incorrect_explanation("The command `git rm --preview` allows you to see files.")
    assert is_incorrect_explanation("Using --preview flag with git rm.")
    assert is_incorrect_explanation("git rm --preview is a handy tool.")


def test_is_incorrect_explanation_detects_missing_path_explanation():
    """Detects when model fails to explain that preview is a path argument."""
    # Mentions git rm and preview, but never explains preview is a path
    content = "In git rm -- preview, `--` ends option parsing. You can use git rm --dry-run -- preview."
    assert is_incorrect_explanation(content)


def test_is_incorrect_explanation_detects_hallucinations():
    """is_incorrect_explanation() must detect every known dangerous misconception pattern."""
    assert is_incorrect_explanation("`git rm -- preview` previews the deletion.")
    assert is_incorrect_explanation("This command activates a preview mode.")
    assert is_incorrect_explanation("It only modifies the index.")
    assert is_incorrect_explanation("It only removes from the index.")
    assert is_incorrect_explanation("It is safe to run git rm -- preview.")
    assert is_incorrect_explanation("preview mode is activated by --")
    assert is_incorrect_explanation("git rm -- exclude=your_file_name")


def test_is_incorrect_explanation_clean_text():
    """is_incorrect_explanation() must NOT flag general accurate statements."""
    assert not is_incorrect_explanation("git rm removes tracked paths from the working tree.")
    assert not is_incorrect_explanation("Use git status --short to inspect changes safely.")
    assert not is_incorrect_explanation("--dry-run previews the removal without deleting files.")


# ---------------------------------------------------------------------------
# verify_and_patch_contradictions — replacement behaviour
# ---------------------------------------------------------------------------

def test_verify_and_patch_replaces_altered_command_content():
    """Model text that changes command to `git rm --preview` must be replaced entirely."""
    notice = DETERMINISTIC_GIT_RM_PREVIEW_NOTICE
    flawed_model_content = (
        "The command `git rm --preview` is a preview option for git rm. "
        "It lets you preview what will be removed."
    )

    result = verify_and_patch_contradictions(notice, flawed_model_content)

    assert notice in result
    assert DETERMINISTIC_GIT_RM_FULL_EXPLANATION in result
    assert "git rm --dry-run -- preview" in result
    assert "git ls-files -- preview" in result

    # Altered command and hallucinated claims must NOT appear
    assert "The command `git rm --preview`" not in result
    assert "preview option for git rm" not in result


def test_verify_and_patch_replaces_contradictory_content():
    """Contradictory model text must be REPLACED, not shown alongside the correction."""
    notice = DETERMINISTIC_GIT_RM_PREVIEW_NOTICE
    contradictory = (
        "Running `git rm -- preview` activates preview mode and previews the deletion. "
        "It only modifies the index and is safe to execute."
    )

    result = verify_and_patch_contradictions(notice, contradictory)

    # Notice must be present
    assert notice in result

    # Deterministic explanation must be present
    assert DETERMINISTIC_GIT_RM_FULL_EXPLANATION in result
    assert "git rm --dry-run -- preview" in result
    assert "git ls-files -- preview" in result

    # Contradictory model text must NOT appear in the final output
    assert "previews the deletion" not in result
    assert "activates preview mode" not in result
    assert "It only modifies the index" not in result
    assert "safe to execute" not in result


def test_verify_and_patch_no_notice_returns_content_unchanged():
    """When no safety notice is triggered the content must be returned as-is."""
    content = "Use git status to check your changes."
    result = verify_and_patch_contradictions(None, content)
    assert result == content


# ---------------------------------------------------------------------------
# /api/chat atomic endpoint regression tests
# ---------------------------------------------------------------------------

def test_chat_endpoint_exact_git_rm_preview_input(client):
    """POST /api/chat with exact input `git rm -- preview`:
    Verifies all core requirements are satisfied:
    1. Returns a deterministic, verified explanation directly from backend.
    2. Does NOT call Ollama or append any model-generated text.
    3. Explains `--` terminates option parsing and `preview` is a path argument, not a flag.
    4. Provides `git rm --dry-run -- preview` as the safe dry-run alternative.
    5. Neither response contains `git rm --preview` or claims it is a valid flag.
    """
    with patch("app.routes.chat.ollama_service.generate_chat", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = ChatResponse(
            content="Hallucinated model text that should never be called",
            model="llama3.2:1b",
            mode="safer_fix",
            created_at=datetime.now(timezone.utc).isoformat(),
            tokens_evaluated=10,
            tokens_generated=10,
        )
        response = client.post(
            "/api/chat",
            json={
                "message": "git rm -- preview",
                "mode": "safer_fix",
                "model": "llama3.2:1b",
            },
        )
        assert response.status_code == 200
        content = response.json()["content"]

        # Ollama must NOT have been called for exact dangerous command
        mock_gen.assert_not_called()

        # 1. Preserves exact command supplied by user
        assert "git rm -- preview" in content
        # 2. Neither response contains `git rm --preview` or claims it is a valid flag
        assert "git rm --preview" not in content
        assert "is a valid flag" not in content.lower()
        assert "--preview is valid" not in content.lower()

        # 3. Explains `--` terminates option parsing and `preview` is a path argument, not a flag
        assert "terminates option parsing" in content.lower()
        assert "path argument" in content.lower()
        assert "not a flag" in content.lower() or "not a preview option" in content.lower()

        # 4. Provides `git rm --dry-run -- preview` as the safe dry-run alternative
        assert "git rm --dry-run -- preview" in content


def test_chat_endpoint_replaces_contradictory_model_output(client):
    """POST /api/chat: contradictory model text must be absent; full explanation must be present."""
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
        content = response.json()["content"]

        # Safety notice must be present
        assert "Deterministic Safety Notice: `git rm` & `--` Argument Semantics" in content
        assert "git status --short" in content

        # Deterministic explanation must replace the model text
        assert "git rm --dry-run -- preview" in content
        assert "git ls-files -- preview" in content
        assert "terminates option parsing" in content

        # Contradictory model claims must be absent
        assert "previews the deletion" not in content
        assert "It only modifies the index" not in content


# ---------------------------------------------------------------------------
# /api/chat/stream endpoint regression tests
# ---------------------------------------------------------------------------

def _parse_sse_chunks(response_text: str) -> list[dict]:
    """Parse SSE lines into a list of event dicts."""
    chunks = []
    for line in response_text.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            try:
                chunks.append(json.loads(line[6:]))
            except json.JSONDecodeError:
                pass
    return chunks


def test_chat_stream_endpoint_exact_git_rm_preview_input(client):
    """POST /api/chat/stream with exact input `git rm -- preview`:
    Verifies all core requirements are satisfied:
    1. Returns a deterministic, verified explanation directly from backend.
    2. Does NOT stream Ollama or append any model-generated text.
    3. Explains `--` terminates option parsing and `preview` is a path argument, not a flag.
    4. Provides `git rm --dry-run -- preview` as the safe dry-run alternative.
    5. Neither response contains `git rm --preview` or claims it is a valid flag.
    """
    with patch("app.routes.chat.ollama_service.stream_chat", new_callable=AsyncMock) as mock_stream:
        response = client.post(
            "/api/chat/stream",
            json={
                "message": "git rm -- preview",
                "mode": "command_oracle",
                "model": "llama3.2:1b",
            },
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Ollama stream must NOT have been called for exact dangerous command
        mock_stream.assert_not_called()

        chunks = _parse_sse_chunks(response.text)
        assert chunks, "Expected SSE chunks"

        all_text = "".join(c.get("content", "") for c in chunks)

        # 1. Exact command preserved
        assert "git rm -- preview" in all_text
        # 2. Neither response contains `git rm --preview` or claims it is a valid flag
        assert "git rm --preview" not in all_text
        assert "is a valid flag" not in all_text.lower()
        assert "--preview is valid" not in all_text.lower()

        # 3. Required explanations present
        assert "terminates option parsing" in all_text.lower()
        assert "path argument" in all_text.lower()

        # 4. Safe dry-run alternative
        assert "git rm --dry-run -- preview" in all_text


def test_chat_stream_endpoint_replaces_contradictory_chunks(client):
    """POST /api/chat/stream: contradictory model chunks must be absent; full explanation present."""
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

        chunks = _parse_sse_chunks(response.text)
        assert chunks, "Expected at least one SSE event"

        # Chunk 0: deterministic safety preface
        first = chunks[0]
        assert "Deterministic Safety Notice: `git rm` & `--` Argument Semantics" in first["content"]
        assert "git status --short" in first["content"]

        # Reconstruct everything visible to the client
        all_text = "".join(c.get("content", "") for c in chunks)

        # Deterministic explanation must be present
        assert "git rm --dry-run -- preview" in all_text
        assert "git ls-files -- preview" in all_text
        assert "terminates option parsing" in all_text

        # Contradictory model text must be absent
        assert "activates preview mode" not in all_text
        assert "only modifies the index." not in all_text


def test_chat_stream_contradiction_split_across_chunk_boundary(client):
    """Contradiction split across two chunks must still be detected and suppressed."""
    async def mock_split_boundary_stream(*args, **kwargs):
        # Pattern "preview mode" split across chunks
        yield {"content": "This command activates a pre", "done": False, "model": "llama3.2:1b"}
        yield {"content": "view mode for deletions.", "done": False, "model": "llama3.2:1b"}
        yield {"content": "", "done": True, "model": "llama3.2:1b", "tokens_generated": 10}

    with patch("app.routes.chat.ollama_service.stream_chat", side_effect=mock_split_boundary_stream):
        response = client.post(
            "/api/chat/stream",
            json={
                "message": "explain git rm -- preview",
                "mode": "safer_fix",
                "model": "llama3.2:1b",
            },
        )
        assert response.status_code == 200

        chunks = _parse_sse_chunks(response.text)
        all_text = "".join(c.get("content", "") for c in chunks)

        # Deterministic explanation must replace the split contradictory text
        assert "git rm --dry-run -- preview" in all_text
        # The contradiction joined across chunks must not appear in the output
        assert "activates a preview mode" not in all_text
