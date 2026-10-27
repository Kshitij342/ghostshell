"""Regression tests for GhostShell system prompt templates, guardrails, and request parameters."""

from app.config import settings
from app.services.ollama_service import ollama_service
from app.services.prompt_templates import BASE_SAFETY_GUARDRAILS, get_system_prompt


def test_base_safety_guardrails_integrity():
    """Verify core boundaries: no execution, untrusted input, accurate safety claims, no fabricated dependencies."""
    assert "You do NOT possess autonomous execution capabilities" in BASE_SAFETY_GUARDRAILS
    assert "NEVER claim that you have executed commands" in BASE_SAFETY_GUARDRAILS
    assert "UNTRUSTED DATA" in BASE_SAFETY_GUARDRAILS
    assert "Never label any command as safe, reversible, a dry run, or a preview" in BASE_SAFETY_GUARDRAILS
    assert "pycurl" in BASE_SAFETY_GUARDRAILS
    assert "requests" in BASE_SAFETY_GUARDRAILS
    assert "concise" in BASE_SAFETY_GUARDRAILS.lower()


def test_error_exorcist_prompt_requirements():
    """Verify Error Exorcist prompt guidelines for accuracy, root causes, and Python imports."""
    prompt = get_system_prompt("error_exorcist")

    # 1. Prioritize most likely cause & distinguish facts from possibilities
    assert "Prioritize the simplest and most probable root cause first" in prompt
    assert "Distinguish verified facts" in prompt
    assert "Alternative Possibilities" in prompt

    # 2. ModuleNotFoundError & requests guidance
    assert "ModuleNotFoundError: No module named 'requests'" in prompt
    assert "active Python environment" in prompt
    assert "different Python interpreter" in prompt
    assert "python -m pip install" in prompt

    # 3. Guard against unsupported claims (pycurl, pip vs setuptools)
    assert "pycurl" in prompt

    # 4. Avoid redundancy across headings
    assert "Avoid redundancy" in prompt or "do not repeat" in prompt.lower()

    # 5. Required structured sections
    assert "Error Summary" in prompt
    assert "Most Likely Cause" in prompt
    assert "Step-by-Step Troubleshooting" in prompt
    assert "Recommended Fix" in prompt
    assert "Precautions" in prompt


def test_safer_fix_critical_facts_and_read_only_alternatives():
    """Verify Safer Fix prompt explicitly contains critical parsing facts, no invented previews, and read-only inspection."""
    prompt = get_system_prompt("safer_fix")

    # Critical Fact 1: `--` separates options from path arguments; not a preview flag
    assert "The token `--` separates command options from path arguments; it is NOT a preview flag." in prompt

    # Critical Fact 2: `git rm` removes tracked files from working tree and stages removal
    assert "`git rm` removes tracked files from the working tree and stages their removal by default." in prompt

    # Critical Fact 3: `git rm -- preview` treats preview as a path argument, not preview mode
    assert "`git rm -- preview` treats `preview` as a path argument" in prompt
    assert "Never invent a file-browser preview or claim preview functionality exists" in prompt

    # Critical Fact 4: Suggest read-only inspection commands
    assert "git status --short" in prompt
    assert "git ls-files" in prompt
    assert "Get-ChildItem" in prompt
    assert "ls" in prompt

    # Critical Fact 5: Prefer read-only alternative when user wants to inspect
    assert "Prefer a read-only alternative whenever the user only wants to inspect files." in prompt

    # Critical Fact 6: Never label command as safe/dry run unless accurate
    assert "Never label a command as safe, reversible, a dry run, or a preview unless that claim is factually accurate" in prompt

    # Structured sections
    assert "Identified Risk" in prompt
    assert "Safer Strategy" in prompt
    assert "Safer Command / Fix" in prompt
    assert "Verification & Precautions" in prompt


def test_command_oracle_prompt_structure():
    """Verify Command Oracle prompt provides required surgical sections and parsing facts."""
    prompt = get_system_prompt("command_oracle")

    assert "The token `--` separates command options from path arguments" in prompt
    assert "Overview" in prompt
    assert "Flags & Arguments Breakdown" in prompt
    assert "Execution Expectations" in prompt
    assert "Destructive & Security Risks" in prompt
    assert "Safer Alternatives" in prompt


def test_ollama_payload_request_parameters():
    """Verify that Ollama chat payload configures context length, output limits, and low temperature for safety."""
    model, payload = ollama_service._build_payload(
        message="git rm -- preview",
        mode="safer_fix",
        stream=False,
    )

    assert "options" in payload
    opts = payload["options"]

    # Low temperature for deterministic, factual outputs on small models
    assert opts["temperature"] == 0.2

    # Context window & token prediction limits configured
    assert opts["num_ctx"] == settings.ollama_num_ctx
    assert opts["num_predict"] == settings.ollama_num_predict
    assert opts["top_p"] == 0.9

    # Message structure check
    assert len(payload["messages"]) >= 2
    assert payload["messages"][0]["role"] == "system"
    assert "The token `--` separates command options from path arguments" in payload["messages"][0]["content"]
    assert payload["messages"][-1]["content"] == "git rm -- preview"
