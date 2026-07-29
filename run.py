"""
Convenience launcher. On mine's WSL/Windows machine, prefer the repo shell
launcher so the canonical conda work Python is used:
  scripts/ia --help
  scripts/ia portfolio add AAPL 10 --cost 150

Direct use still works when the current Python has project dependencies:
  python run.py --help
"""
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # Keep --help usable before optional setup dependencies are installed.
    load_dotenv = None

PROJECT_ROOT = Path(__file__).parent

# Force UTF-8 output on Windows to handle Unicode in LLM responses
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Load project-local environment variables before importing application code.
# This makes `cp .env.example .env` a real setup path for fresh agents/shells.
if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")

# Ensure the project root is on the path
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app

if __name__ == "__main__":
    app()
