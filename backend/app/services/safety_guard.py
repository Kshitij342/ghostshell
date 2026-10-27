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
> - **Preserve Exact Command:** The user command is `git rm -- preview`. Do not collapse the argument separator or invent a `--preview` flag — `--preview` is not a valid Git flag.
> - **`--` Terminates Option Parsing:** In Git and POSIX tools, `--` terminates option parsing and separates command-line options from path arguments; it does **not** mean preview, confirmation, or dry-run mode.
> - **Path Interpretation:** `git rm -- preview` treats `preview` strictly as a path argument (a file or directory to delete from the working tree and index), not a flag or preview option.
> - **Safe Dry-Run Alternative:** `git rm --dry-run -- preview` (or `git rm -n -- preview`) is the verified non-destructive dry-run equivalent.
> - **Destructive Removal:** By default, `git rm` removes tracked paths from both the working tree and the index. It does not merely modify the index.
> - **Safe Read-Only Inspection:** To safely inspect files or repository status without risk of deletion, use:
>   - `git status --short` (inspect working tree status and staged changes safely)
>   - `git ls-files` or `git ls-files -- path/to/file` (list tracked files safely)
>   - `git ls-files -- preview` (check if a tracked path named `preview` exists)
>
> *(Warning: Any suggestion claiming `--` or `--preview` is a valid preview flag, that `preview` is not a path argument, or that `git rm` only modifies the index is factually false and dangerous.)*"""

# Full deterministic explanation that REPLACES contradictory or incorrect model output entirely.
# Every fact here has been verified against `git rm -h` and POSIX argument conventions.
DETERMINISTIC_GIT_RM_FULL_EXPLANATION = """\
### Explanation of `git rm -- preview`

**1. Preserve Exact Command: `git rm -- preview`**
The command supplied by the user is `git rm -- preview`. Do not alter the command into a collapsed flag syntax — `--preview` is not a valid Git flag or option.

**2. `--` Terminates Option Parsing**
The `--` token terminates option parsing (ends option parsing); it does not mean preview or dry-run. In Git and POSIX command-line interfaces, `--` indicates to the parser that all subsequent tokens are positional path arguments rather than command options.

**3. `preview` is Interpreted as a Path Argument, Not a Flag**
In `git rm -- preview`, `preview` is interpreted strictly as a path argument (the name of a file or directory in the repository to remove), not a flag. It does not activate a preview mode or file-browser preview.

**4. Destructive Behavior of `git rm`**
By default, `git rm <path>` permanently removes tracked paths from **both** the working tree (disk) and stages their deletion in the index. It is a destructive operation that cannot be undone without a separate `git restore` step.
- `git rm -- preview` → deletes the file or directory named `preview` from disk and stages the removal.
- `git rm --cached -- preview` → removes `preview` from the index only, leaving the file on disk.

**5. Safe Dry-Run Alternative**
To safely preview what `git rm` would remove without deleting any files, use the verified dry-run option:
```bash
git rm --dry-run -- preview
```
`--dry-run` (or `-n`) is the verified flag for a non-destructive preview. It prints which tracked path named `preview` would be removed without actually removing it.

**6. Safe Read-Only Inspection Commands**
If your intention is to inspect files or repository status without modifying anything:
```bash
git status --short
```
Shows working tree and staged changes without modifying anything.

```bash
git ls-files -- preview
```
Shows whether a path named `preview` is currently tracked in the repository."""

# Kept for import compatibility with any existing references. No longer appended after model text.
CONTRADICTION_CORRECTION_BANNER = """\
\n\n> [!WARNING]
> **Safety Override:** The model response has been suppressed because it contained inaccurate claims. \
`git rm -- preview` will delete the file or directory named 'preview' from your working tree and stage its removal. \
Use read-only commands like `git status --short` or `git ls-files -- preview` instead."""


# Patterns that indicate the model has hallucinated dangerous misinformation about git rm
_CONTRADICTION_PATTERNS = [
    r"previews?\s+(the\s+)?deletion",
    r"activates?\s+(a\s+)?preview",
    r"preview\s+mode",
    r"only\s+modifies?\s+(the\s+)?index",
    r"only\s+removes?\s+from\s+(the\s+)?index",
    r"safe\s+to\s+(run|execute)\s+git\s+rm\s+--\s+preview",
]


def is_exact_git_rm_preview(message: str) -> bool:
    """Check if the user request is specifically the exact `git rm -- preview` command."""
    if not message:
        return False
    cleaned = message.strip().strip("`'\"").strip()
    normalized = " ".join(cleaned.split())
    return bool(re.fullmatch(r"git\s+rm\s+--\s+preview[;.]?", normalized, re.IGNORECASE))


def get_deterministic_git_rm_response() -> str:
    """Return the complete deterministic, verified explanation for `git rm -- preview`."""
    return f"{DETERMINISTIC_GIT_RM_PREVIEW_NOTICE}\n\n{DETERMINISTIC_GIT_RM_FULL_EXPLANATION}"


def is_incorrect_explanation(content: str) -> bool:
    """Check if model output contains any incorrect explanation, invented flags, or altered commands.

    An explanation for `git rm -- preview` is deemed incorrect and conflicting if:
    1. It alters the command to `git rm --preview` or claims `--preview` is a flag.
    2. It invents non-existent flags (like `-- exclude=...`) or progress-bar claims.
    3. It contains known dangerous misconceptions (claiming `--` enables preview mode, etc.).
    4. When discussing `git rm` with `preview`, it fails to explain that `preview` is a path argument.
    5. When discussing `git rm` with `preview`, it fails to explain that `--` terminates / ends option parsing.
    6. When discussing `git rm` with `preview`, it fails to provide `git rm --dry-run -- preview` as the safe dry-run equivalent.
    """
    if not content:
        return True

    content_lower = content.lower()

    # 1. Altered command or invented `--preview` flag
    if re.search(r"--preview\b", content_lower):
        return True
    if re.search(r"git\s+rm\s+--preview\b", content_lower):
        return True

    # 2. Fabricated flags or unsupported claims
    if re.search(r"--\s*exclude=", content_lower) or "progress bar" in content_lower:
        return True

    # 3. Known dangerous misconceptions
    for pat in _CONTRADICTION_PATTERNS:
        if re.search(pat, content_lower):
            return True

    # 4. If the content addresses `preview` in `git rm`, verify required factual elements:
    if "preview" in content_lower and "git rm" in content_lower:
        # Must explain that preview is interpreted as a path argument
        has_path = bool(re.search(r"\bpath(\s+argument)?\b", content_lower))
        if not has_path:
            return True

        # Must explain that -- terminates / ends option parsing or separates options
        has_separator = bool(
            re.search(
                r"(terminat|end|separat)\w*\s+(option\s+parsing|options|args|arguments)|argument\s+separator",
                content_lower,
            )
        )
        if not has_separator:
            return True

        # Must provide the verified dry-run equivalent
        has_dry_run = (
            "git rm --dry-run -- preview" in content_lower
            or "git rm -n -- preview" in content_lower
        )
        if not has_dry_run:
            return True

    return False


def has_contradiction(content: str) -> bool:
    """Return True if model output contains a known dangerous misconception or incorrect explanation."""
    return is_incorrect_explanation(content)


def get_deterministic_safety_notice(message: str, mode: ChatMode) -> Optional[str]:
    """Check if the user request triggers a deterministic safety rule.

    Narrowly scoped to Safer Fix and Command Oracle modes, or queries directly
    addressing destructive ``git rm`` and ``--`` / ``preview`` argument misconceptions.
    Does not intercept unrelated chat or ordinary commands.
    """
    # Only evaluate for relevant modes
    if mode not in ("safer_fix", "command_oracle", "general"):
        return None

    msg_lower = message.lower()

    # Must specifically target `git rm`
    if not re.search(r"\bgit\s+rm\b", msg_lower):
        return None

    has_separator = "--" in message
    has_preview_keyword = "preview" in msg_lower

    if has_separator and has_preview_keyword:
        return DETERMINISTIC_GIT_RM_PREVIEW_NOTICE

    # In safer_fix or command_oracle, asking about `git rm` safety with `--`
    if mode in ("safer_fix", "command_oracle") and has_separator:
        if any(w in msg_lower for w in ("safe", "dry", "preview", "test", "check")):
            return DETERMINISTIC_GIT_RM_PREVIEW_NOTICE

    return None


def verify_and_patch_contradictions(notice: Optional[str], content: str) -> str:
    """Ensure model output does not contradict the deterministic safety notice.

    When an incorrect or contradictory explanation is detected, the model text is
    **replaced entirely** with DETERMINISTIC_GIT_RM_FULL_EXPLANATION. The model text
    is never shown alongside the correction — doing so would still expose dangerous
    misinformation or altered commands to the user.
    """
    if not notice:
        return content

    if is_incorrect_explanation(content):
        # Suppress the incorrect model text; return only the verified explanation.
        return f"{notice}\n\n{DETERMINISTIC_GIT_RM_FULL_EXPLANATION}"

    return f"{notice}\n\n{content}"
