"""Runtime locations are explicit and independent of the caller's cwd."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / 'data'
DEFAULT_WORKSPACE = ROOT / 'workspace'
