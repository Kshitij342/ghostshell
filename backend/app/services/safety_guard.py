"""Deterministic safety layer for GhostShell.

Provides narrowly scoped, grounded safety notices and contradiction guards
for dangerous command misconceptions (e.g., git rm -- preview).
"""

import re
from typing import Optional
from app.schemas.chat import ChatMode

DETERMINISTIC_GIT_RM_PREVIEW_NOTICE = """\
> [!CAUTION]
> **Deterministic Safety Notice: `git rm` & `--` Argument Semantics**
> - **`--` is an Argument Separator:** In Git and POSIX tools, `--` separates command-line options from path arguments; it does **not** enable preview, confirmation, or dry-run mode.
> - **Path Interpretation:** `git rm -- preview` treats `preview` strictly as a path argument (a file or directory to delete).
> - **Destructive Removal:** By default, `git rm` removes tracked paths from both the working tree and the index. It does not merely modify the index.
> - **Safe Read-Only Inspection:** To safely inspect files or repository status without risk of deletion, use:
>   - `git status --short` (inspect working tree status and staged changes)
>   - `git ls-files` or `git ls-files -- path/to/file` (list tracked files safely)
>
> *(Warning: Any suggestion claiming `git rm -- preview` is a preview flag, only modifies the index, or is safe to run without deleting files is factually false and dangerous.)*"""

CONTRADICTION_CORRECTION_BANNER = """\
\n\n> [!WARNING]
> **Safety Override:** The model text above contains inaccurate claims. `git rm -- preview` will delete the file or directory named 'preview' from your working tree and stage its removal. Use read-only commands like `git status --short` or `git ls-files` instead."""


def get_deterministic_safety_notice(message: str, mode: ChatMode) -> Optional[str]:
    """Check if the user request triggers a deterministic safety rule.

    Narrowly scoped to Safer Fix and Command Oracle modes, or queries directly
    addressing destructive `git rm` and `--` / `preview` argument misconceptions.
    Does not intercept unrelated chat or ordinary commands.
    """
    # Only evaluate for relevant modes or explicit command inquiries
    if mode not in ("safer_fix", "command_oracle", "general"):
        return None

    msg_lower = message.lower()

    # Must specifically target `git rm`
    if not re.search(r"\bgit\s+rm\b", msg_lower):
        return None

    # Must specifically target the `--` separator or `preview` argument misconception
    has_separator = "--" in message
    has_preview_keyword = "preview" in msg_lower

    if has_separator and has_preview_keyword:
        return DETERMINISTIC_GIT_RM_PREVIEW_NOTICE

    # In safer_fix or command_oracle, if asking about `git rm` safety with `--`
    if mode in ("safer_fix", "command_oracle") and has_separator:
        # Check if checking safety, dry run, or preview
        if any(w in msg_lower for w in ("safe", "dry", "preview", "test", "check")):
            return DETERMINISTIC_GIT_RM_PREVIEW_NOTICE

    return None


def verify_and_patch_contradictions(notice: Optional[str], content: str) -> str:
    """If a deterministic safety notice was triggered, ensure model output does not contradict it."""
    if not notice:
        return content

    content_lower = content.lower()

    # Detect known dangerous misconceptions in model-generated output
    contradiction_patterns = [
        r"previews?\s+(the\s+)?deletion",
        r"activates?\s+(a\s+)?preview",
        r"preview\s+mode",
        r"only\s+modifies?\s+(the\s+)?index",
        r"only\s+removes?\s+from\s+(the\s+)?index",
        r"safe\s+to\s+(run|execute)\s+git\s+rm\s+--\s+preview",
    ]

    has_contradiction = any(re.search(pat, content_lower) for pat in contradiction_patterns)

    if has_contradiction:
        return f"{notice}\n\n{content}{CONTRADICTION_CORRECTION_BANNER}"

    return f"{notice}\n\n{content}"
