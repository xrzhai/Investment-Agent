"""
LLM client — delegates to a configured CLI via subprocess.

Defaults:
- command: `claude`
- args: `--print --tools '' --no-session-persistence`

Override with:
- `INVESTMENT_AGENT_LLM_CMD`
- `INVESTMENT_AGENT_LLM_ARGS`

The configured command is expected to support the same non-interactive calling
pattern used below.
"""
from __future__ import annotations

import os
import shlex
import subprocess

DEFAULT_LLM_CMD = "claude"
DEFAULT_LLM_ARGS = ["--print", "--tools", "", "--no-session-persistence"]


def _llm_cmd() -> str:
    return os.environ.get("INVESTMENT_AGENT_LLM_CMD", DEFAULT_LLM_CMD)


def _llm_args() -> list[str]:
    raw = os.environ.get("INVESTMENT_AGENT_LLM_ARGS")
    if not raw:
        return list(DEFAULT_LLM_ARGS)
    return shlex.split(raw)


def call_llm(prompt: str, system: str = "You are a disciplined investment copilot. Use plain text only. Do not use emoji or special Unicode symbols.") -> str:
    """Send a prompt to the configured LLM CLI and return the response text."""
    llm_cmd = _llm_cmd()
    cmd = [
        llm_cmd,
        *_llm_args(),
        "--system-prompt", system,
        prompt,
    ]

    env = dict(os.environ)
    if llm_cmd == "claude":
        # Avoid nested-session behavior when the configured backend is Claude CLI.
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
            f"The configured LLM CLI `{llm_cmd}` was not found. Install it or set INVESTMENT_AGENT_LLM_CMD to a compatible command."
        ) from None
    except subprocess.TimeoutExpired:
        raise RuntimeError("LLM call timed out after 120 seconds.") from None

    if result.returncode != 0:
        raise RuntimeError(
            f"`{llm_cmd}` exited with code {result.returncode}. stderr: {result.stderr.strip()[:400]}"
        )

    response = result.stdout.strip()
    if not response:
        raise RuntimeError(f"`{llm_cmd}` returned an empty response. stderr: {result.stderr.strip()[:400]}")

    return response
