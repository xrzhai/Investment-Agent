#!/usr/bin/env python3
"""Lightweight setup doctor for Investment-Agent.

This script checks reproducible setup prerequisites without printing secret values.
It is safe to run before dependencies are fully installed: missing packages are
reported as setup gaps instead of importing application code.

On mine's Windows/WSL machine, project Python dependencies usually live in the
Windows conda `work` environment. If this doctor is started from Hermes' WSL
Python, it re-runs itself with the canonical project Python to avoid false
"missing dependency" reports.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MINE_WORK_PYTHON = (
    Path(r"C:\Users\zhaix\miniconda3\envs\work\python.exe")
    if os.name == "nt"
    else Path("/mnt/c/Users/zhaix/miniconda3/envs/work/python.exe")
)


def resolve_canonical_python() -> Path:
    """Return the intended Python runtime for this repo.

    Override order:
    1. INVESTMENT_AGENT_PYTHON — repo-specific override.
    2. MINE_WORK_PYTHON — machine-wide local convention.
    3. Windows conda work env path used on mine's current WSL machine.
    """
    for env_name in ("INVESTMENT_AGENT_PYTHON", "MINE_WORK_PYTHON"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return Path(value)
    return DEFAULT_MINE_WORK_PYTHON


def _norm_path(value: str | Path) -> str:
    try:
        return str(Path(value).resolve(strict=False)).lower()
    except OSError:
        return str(value).lower()


def should_reexec(*, current_python: str | Path, canonical_python: Path, already_reexeced: bool) -> bool:
    """Return True when the doctor should re-run under the canonical runtime."""
    if already_reexeced:
        return False
    if not canonical_python.exists():
        return False
    return _norm_path(current_python) != _norm_path(canonical_python)


WINDOWS_SECRET_ENV_NAMES = (
    "JQ_USER",
    "JQ_PASS",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "TAVILY_API_KEY",
    "BROWSER_USE_API_KEY",
    "BROWSERUSE_API_KEY",
)


def build_windows_wslenv(*, existing: str = "", environ: dict[str, str] | None = None) -> str:
    """Expose present project env names when re-execing from WSL to Windows Python."""
    env = os.environ if environ is None else environ
    parts = [part for part in existing.split(":") if part]
    seen = set(parts)
    for name in WINDOWS_SECRET_ENV_NAMES:
        if env.get(name):
            entry = f"{name}/w"
            if entry not in seen:
                parts.append(entry)
                seen.add(entry)
    return ":".join(parts)


def _windows_path_from_wsl(path: Path) -> str:
    """Translate /mnt/<drive>/... to a Windows path for Windows python.exe."""
    parts = path.resolve(strict=False).parts
    if len(parts) >= 4 and parts[1] == "mnt" and len(parts[2]) == 1:
        drive = parts[2].upper()
        rest = "\\".join(parts[3:])
        return f"{drive}:\\{rest}"
    return str(path)


def _maybe_reexec_with_canonical_python(raw_args: list[str], already_reexeced: bool, no_reexec: bool) -> None:
    canonical_python = resolve_canonical_python()
    if no_reexec:
        return
    if not should_reexec(current_python=sys.executable, canonical_python=canonical_python, already_reexeced=already_reexeced):
        return

    script_path = Path(__file__).resolve()
    is_windows_python = canonical_python.suffix.lower() == ".exe"
    script_arg = _windows_path_from_wsl(script_path) if is_windows_python else str(script_path)
    if is_windows_python:
        os.environ["WSLENV"] = build_windows_wslenv(existing=os.environ.get("WSLENV", ""))
    os.execv(str(canonical_python), [str(canonical_python), script_arg, *raw_args, "--_reexeced"])


def _load_dotenv() -> bool:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False
    load_dotenv(ROOT / ".env")
    return True


def _has_env(name: str) -> bool:
    return bool(os.environ.get(name, "").strip())


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description="Check Investment-Agent local setup without leaking secrets")
    parser.add_argument("--strict", action="store_true", help="Treat optional credentials as required")
    parser.add_argument("--no-reexec", action="store_true", help="Check the current Python instead of the canonical project runtime")
    parser.add_argument("--_reexeced", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(raw_args)

    _maybe_reexec_with_canonical_python(raw_args, already_reexeced=args._reexeced, no_reexec=args.no_reexec)

    loaded_dotenv = _load_dotenv()
    ok = True
    canonical_python = resolve_canonical_python()

    print("Investment-Agent setup doctor")
    print(f"repo: {ROOT}")
    print(f"python: {sys.version.split()[0]}")
    print(f"python executable: {sys.executable}")
    print(f"canonical python: {canonical_python if canonical_python.exists() else str(canonical_python) + ' (missing)'}")
    print(f".env: {'present' if (ROOT / '.env').exists() else 'missing'}; dotenv loader: {'available' if loaded_dotenv else 'not installed'}")
    print()

    required_modules = [
        ("typer", "typer"),
        ("pydantic", "pydantic"),
        ("sqlmodel", "sqlmodel"),
        ("yfinance", "yfinance"),
        ("rich", "rich"),
        ("jqdatasdk", "jqdatasdk"),
        ("dotenv", "python-dotenv"),
    ]
    missing_modules = [package for module, package in required_modules if not _module_available(module)]
    if missing_modules:
        ok = False
        print("MISSING packages:")
        for package in missing_modules:
            print(f"  - {package}")
        install_cmd = f"{canonical_python} -m pip install -r requirements.txt" if canonical_python.exists() else "python -m pip install -r requirements.txt"
        print(f"  install: {install_cmd}")
    else:
        print("packages: ok")

    print()
    jq_ready = _has_env("JQ_USER") and _has_env("JQ_PASS")
    print(f"JQData credentials: {'present (optional)' if jq_ready else 'disabled/absent (optional)'}")
    if not jq_ready:
        print("  A-share research defaults to AkShare/THS/Eastmoney + official filings/PDF; JQData is not required")
        if args.strict:
            print("  strict mode: JQData still treated as optional in mine's current setup")

    llm_cmd = os.environ.get("INVESTMENT_AGENT_LLM_CMD", "claude")
    llm_path = shutil.which(llm_cmd)
    print(f"LLM CLI: {llm_cmd} -> {llm_path or 'not found'}")
    if not llm_path:
        print("  LLM-backed analysis commands will fail until this CLI is installed or INVESTMENT_AGENT_LLM_CMD is set")

    print()
    print("secret values: not printed")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
