"""
LLM client — delegates to the `claude` CLI via subprocess.
Requires Claude Code CLI to be installed and authenticated (Claude.ai subscription).
"""
from __future__ import annotations

import os
import subprocess

CLAUDE_BIN = "claude"


def call_llm(prompt: str, system: str = "You are a disciplined investment copilot. Use plain text only. Do not use emoji or special Unicode symbols.") -> str:
    """Send a prompt to Claude via the `claude` CLI and return the response text."""
    cmd = [
        CLAUDE_BIN,
        "--print",
        "--tools", "",
        "--no-session-persistence",
        "--system-prompt", system,
        prompt,
    ]

    # Remove CLAUDECODE so the subprocess is not treated as a nested session.
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            env=env,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "The `claude` CLI was not found. Ensure Claude Code is installed and in PATH."
        ) from None
    except subprocess.TimeoutExpired:
        raise RuntimeError("LLM call timed out after 120 seconds.") from None

    if result.returncode != 0:
        raise RuntimeError(
            f"`claude` exited with code {result.returncode}. stderr: {result.stderr.strip()[:400]}"
        )

    response = result.stdout.strip()
    if not response:
        raise RuntimeError(f"`claude` returned an empty response. stderr: {result.stderr.strip()[:400]}")

    return response
