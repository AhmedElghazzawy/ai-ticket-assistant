"""Where the project's files are. One place, so a moved folder is a one-line change."""

from pathlib import Path

# src/helpdesk/core/paths.py -> the repository root (the package is installed in editable mode,
# so this is the checkout in development and /app in the Docker image).
ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data"
EVAL_DIR = ROOT / "eval"
