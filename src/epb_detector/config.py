"""Runtime configuration for the EPB detector.

All paths and tunable thresholds live here. Override via environment variables
prefixed with ``EPB_``, e.g. ``EPB_ROTI_THRESHOLD=0.4 epb features build``.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Paths(BaseSettings):
    """Filesystem layout. All paths anchored to the repo root by default."""

    model_config = SettingsConfigDict(env_prefix="EPB_PATH_", extra="ignore")

    repo_root: Path = REPO_ROOT
    rinex_input: Path = REPO_ROOT / "INPUT" / "RINEX"
    orbit_input: Path = REPO_ROOT / "INPUT" / "ORBITS"
    pyoasis_output: Path = REPO_ROOT / "OUTPUT"
    data_raw: Path = REPO_ROOT / "data" / "raw"
    data_processed: Path = REPO_ROOT / "data" / "processed"
    data_snapshots: Path = REPO_ROOT / "data" / "training_snapshots"
    data_space_weather: Path = REPO_ROOT / "data" / "space_weather"
    cache: Path = REPO_ROOT / "cache"
    models: Path = REPO_ROOT / "models"
    paper_figures: Path = REPO_ROOT / "paper" / "figures"
    paper_tables: Path = REPO_ROOT / "paper" / "tables"


class LabelConfig(BaseSettings):
    """Weak-label heuristic parameters (Pi 1997 / Cherniak 2014)."""

    model_config = SettingsConfigDict(env_prefix="EPB_LABEL_", extra="ignore")

    rule_version: str = "weak-v1"
    roti_threshold_tecu_per_min: float = 0.5
    sustained_minutes: float = 5.0
    night_local_time_start: float = 19.0  # hours
    night_local_time_end: float = 6.0  # hours (wraps midnight)
    multi_sat_min_count: int = 2
    multi_sat_lon_window_deg: float = 10.0
    qd_lat_max_abs_deg: float = 20.0


class FeatureConfig(BaseSettings):
    """Feature-extraction window settings."""

    model_config = SettingsConfigDict(env_prefix="EPB_FEAT_", extra="ignore")

    window_minutes: float = 10.0
    stride_minutes: float = 2.5
    # ROTI is computed at 2.5-min cadence by pyOASIS, so a 10-min window can
    # contain at most ~4 samples. Three is the lower bound for a meaningful
    # mean / slope estimate.
    min_window_samples: int = 3
    elevation_min_deg: float = 30.0


class TrainConfig(BaseSettings):
    """Training defaults."""

    model_config = SettingsConfigDict(env_prefix="EPB_TRAIN_", extra="ignore")

    n_splits: int = 5
    random_seed: int = 42
    pr_auc_floor: float = 0.75  # CI gate for Phase 1


class Settings(BaseSettings):
    """Top-level settings container."""

    model_config = SettingsConfigDict(env_prefix="EPB_", extra="ignore")

    paths: Paths = Field(default_factory=Paths)
    labels: LabelConfig = Field(default_factory=LabelConfig)
    features: FeatureConfig = Field(default_factory=FeatureConfig)
    train: TrainConfig = Field(default_factory=TrainConfig)


def get_settings() -> Settings:
    return Settings()


SETTINGS = get_settings()
