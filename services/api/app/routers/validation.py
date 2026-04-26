"""Case-study validation route.

Surfaces the JSON written by ``case_study_validation_v2.py`` (or any
later vN). The script lives outside the API service — we just read its
output. Picks the lexicographically latest ``case_study_validation_v*.json``
under ``/data`` so re-running validation against a newer model_id
automatically takes effect.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/validation", tags=["validation"])


def _latest_validation_path() -> Path | None:
    # The validation JSON is written by the offline script directly under
    # /data inside the api container's volume — not under SETTINGS.paths
    # because it isn't a feature/label/snapshot artefact.
    candidates = sorted(Path("/data").glob("case_study_validation_v*.json"))
    return candidates[-1] if candidates else None


@router.get("/case-studies")
def case_studies() -> dict:
    """Return the latest case-study validation report verbatim.

    Includes per-event detail (date, reference, expected vs ingested vs
    detected stations) plus aggregate recall. The frontend renders cards
    from this directly.
    """
    path = _latest_validation_path()
    if path is None or not path.exists():
        raise HTTPException(
            status_code=404,
            detail="No case_study_validation_v*.json found under /data",
        )
    return json.loads(path.read_text())
