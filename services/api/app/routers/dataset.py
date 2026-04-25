"""Training-data snapshot inspection endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from epb_detector.config import SETTINGS

router = APIRouter(prefix="/training-data", tags=["training-data"])


def _snap_dir(snapshot_id: str) -> Path:
    return SETTINGS.paths.data_snapshots / snapshot_id


@router.get("/snapshots")
def list_snapshots() -> list[str]:
    base = SETTINGS.paths.data_snapshots
    if not base.exists():
        return []
    return sorted(p.name for p in base.iterdir() if p.is_dir())


@router.get("/snapshots/{snapshot_id}")
def snapshot_meta(snapshot_id: str) -> dict:
    meta_path = _snap_dir(snapshot_id) / "meta.json"
    if not meta_path.exists():
        raise HTTPException(status_code=404, detail=f"Unknown snapshot {snapshot_id!r}")
    return json.loads(meta_path.read_text())


@router.get("/snapshots/{snapshot_id}/distribution")
def feature_distribution(
    snapshot_id: str,
    feature: str,
    bins: int = Query(default=30, ge=4, le=200),
) -> dict:
    snap = _snap_dir(snapshot_id)
    feat_path = snap / "features.parquet"
    label_path = snap / "labels.parquet"
    if not feat_path.exists():
        raise HTTPException(status_code=404, detail=f"Unknown snapshot {snapshot_id!r}")
    con = duckdb.connect()
    try:
        df = con.execute(
            f"""
            SELECT f.{feature} AS value, l.label
            FROM parquet_scan('{feat_path}') f
            JOIN parquet_scan('{label_path}') l USING (window_id)
            WHERE f.{feature} IS NOT NULL
            """
        ).df()
    except duckdb.BinderException as e:
        raise HTTPException(status_code=400, detail=f"Unknown feature {feature!r}") from e
    finally:
        con.close()
    if df.empty:
        return {"feature": feature, "bins": [], "negative": [], "positive": []}
    edges = pd.cut(df["value"], bins=bins, retbins=True, include_lowest=True)[1]
    neg = (
        pd.cut(df.loc[df["label"] == 0, "value"], bins=edges).value_counts().sort_index().tolist()
    )
    pos = (
        pd.cut(df.loc[df["label"] == 1, "value"], bins=edges).value_counts().sort_index().tolist()
    )
    return {
        "feature": feature,
        "bins": edges.tolist(),
        "negative": [int(x) for x in neg],
        "positive": [int(x) for x in pos],
    }


@router.get("/snapshots/{snapshot_id}/sample")
def stratified_sample(
    snapshot_id: str,
    n: int = Query(default=100, ge=1, le=2000),
    seed: int = Query(default=42),
) -> list[dict]:
    snap = _snap_dir(snapshot_id)
    if not (snap / "features.parquet").exists():
        raise HTTPException(status_code=404, detail=f"Unknown snapshot {snapshot_id!r}")
    feats = pd.read_parquet(snap / "features.parquet")
    labels = pd.read_parquet(snap / "labels.parquet")
    df = feats.merge(labels, on="window_id", how="inner")
    half = max(1, n // 2)
    pos = df[df["label"] == 1].sample(n=min(half, (df["label"] == 1).sum()), random_state=seed) \
        if (df["label"] == 1).any() else df.iloc[0:0]
    neg = df[df["label"] == 0].sample(
        n=min(n - len(pos), (df["label"] == 0).sum()), random_state=seed
    ) if (df["label"] == 0).any() else df.iloc[0:0]
    out = pd.concat([pos, neg], ignore_index=True)
    return out.to_dict(orient="records")


@router.get("/snapshots/{snapshot_id}/download.parquet")
def download_features(snapshot_id: str) -> FileResponse:
    feat_path = _snap_dir(snapshot_id) / "features.parquet"
    if not feat_path.exists():
        raise HTTPException(status_code=404, detail=f"Unknown snapshot {snapshot_id!r}")
    return FileResponse(
        feat_path,
        filename=f"features_{snapshot_id}.parquet",
        media_type="application/octet-stream",
    )
