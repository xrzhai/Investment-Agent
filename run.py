"""
Convenience launcher. Run from the project root:
  python run.py --help
  python run.py portfolio add AAPL 10 --cost 150
"""
import sys
from pathlib import Path

# Force UTF-8 output on Windows to handle Unicode in LLM responses
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Ensure the project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app

if __name__ == "__main__":
    app()
