"""Smoke tests for the FastAPI routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.app.main import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_stations_list_includes_mvp(client: TestClient) -> None:
    r = client.get("/stations")
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()}
    assert {"BOAV", "SALU", "POAL"}.issubset(ids)


def test_station_detail(client: TestClient) -> None:
    r = client.get("/stations/SALU")
    assert r.status_code == 200
    assert r.json()["region"] == "eia-crest-south"


def test_unknown_station_404(client: TestClient) -> None:
    r = client.get("/stations/XXXX")
    assert r.status_code == 404


def test_events_endpoint_returns_list(client: TestClient) -> None:
    r = client.get("/events")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_events_summary(client: TestClient) -> None:
    r = client.get("/events/summary")
    assert r.status_code == 200
    assert "total" in r.json()


def test_training_data_snapshots(client: TestClient) -> None:
    r = client.get("/training-data/snapshots")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_storms_catalog_returns_list(client: TestClient) -> None:
    r = client.get("/storms/catalog")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_storms_by_phase_has_rows_key(client: TestClient) -> None:
    r = client.get("/storms/by-phase")
    assert r.status_code == 200
    assert "rows" in r.json()


def test_storms_superposed_epoch(client: TestClient) -> None:
    r = client.get("/storms/superposed-epoch")
    assert r.status_code == 200
    assert "rows" in r.json()


def test_ingest_status_has_counts(client: TestClient) -> None:
    r = client.get("/ingest/status")
    assert r.status_code == 200
    body = r.json()
    for key in ("total", "ok", "failed", "skipped", "by_station"):
        assert key in body


def test_ingest_recent(client: TestClient) -> None:
    r = client.get("/ingest/recent?limit=5")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
