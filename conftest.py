"""Repo-level pytest config.

Ensures ``services/`` (the FastAPI sub-project) is importable from anywhere
the test runner is launched.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
