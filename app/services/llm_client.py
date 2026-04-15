"""
LLM client — delegates to a configured CLI via subprocess.

Default backend command: `claude`.
Override with the `INVESTMENT_AGENT_LLM_CMD` environment variable.
The configured command is expected to support the same non-interactive flags
used below.
"""
from __future__ import annotations

import os
import subprocess

LLM_CMD = os.environ.get("INVESTMENT_AGENT_LLM_CMD", "claude")


def call_llm(prompt: str, system: str = "You are a disciplined investment copilot. Use plain text only. Do not use emoji or special Unicode symbols.") -> str:
    """Send a prompt to the configured LLM CLI and return the response text."""
    cmd = [
        LLM_CMD,
        "--print",
        "--tools", "",
        "--no-session-persistence",
        "--system-prompt", system,
        prompt,
    ]

    env = dict(os.environ)
    if LLM_CMD == "claude":
        # Remove CLAUDECODE so a nested Hermes/Claude session is not treated as a nested Claude Code session.
        env.pop("CLAUDECODE", None)

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
            f"The configured LLM CLI `{LLM_CMD}` was not found. Install it or set INVESTMENT_AGENT_LLM_CMD to a compatible command."
        ) from None
    except subprocess.TimeoutExpired:
        raise RuntimeError("LLM call timed out after 120 seconds.") from None

    if result.returncode != 0:
        raise RuntimeError(
            f"`{LLM_CMD}` exited with code {result.returncode}. stderr: {result.stderr.strip()[:400]}"
        )

    response = result.stdout.strip()
    if not response:
        raise RuntimeError(f"`{LLM_CMD}` returned an empty response. stderr: {result.stderr.strip()[:400]}")

    return response
