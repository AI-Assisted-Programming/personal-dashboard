"""Tests for the Flask application routes."""

from __future__ import annotations

import datetime as dt

import pytest

import dashboard.app as app_module
from dashboard.app import create_app
from dashboard.config import Settings
from dashboard.services import GitHubActivity, Weather


@pytest.fixture
def client(monkeypatch):
    fixed_time = dt.datetime(2026, 10, 8, 9, 30, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(app_module, "get_current_time", lambda tz: fixed_time)
    monkeypatch.setattr(
        app_module,
        "get_weather",
        lambda settings: Weather(
            location="Wrocław, Poland",
            temperature_c=12.5,
            apparent_temperature_c=10.0,
            wind_speed_kmh=15.0,
            description="Partly cloudy",
            observed_at=fixed_time,
        ),
    )
    monkeypatch.setattr(
        app_module,
        "get_github_activity",
        lambda settings: GitHubActivity(
            repo="All-Hands-AI/OpenHands",
            issues_opened=3,
            pull_requests_opened=4,
            window_hours=24,
            since=fixed_time - dt.timedelta(hours=24),
        ),
    )
    app = create_app(settings=Settings(github_token="x"))
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        yield test_client


def test_index_renders_all_sections(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "09:30:00" in body
    assert "12.5" in body
    assert "Partly cloudy" in body
    assert "All-Hands-AI/OpenHands" in body
    assert ">3<" in body
    assert ">4<" in body


def test_api_data_returns_json(client):
    response = client.get("/api/data")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["time"].startswith("2026-10-08T09:30:00")
    assert payload["weather"]["temperature_c"] == 12.5
    assert payload["activity"]["issues_opened"] == 3
    assert payload["activity"]["pull_requests_opened"] == 4
    assert payload["errors"] == {"time": None, "weather": None, "activity": None}


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_sections_isolate_failures(monkeypatch):
    def boom(*args, **kwargs):
        raise app_module.DashboardError("weather down")

    fixed_time = dt.datetime(2026, 10, 8, 9, 30, tzinfo=dt.timezone.utc)
    monkeypatch.setattr(app_module, "get_current_time", lambda tz: fixed_time)
    monkeypatch.setattr(app_module, "get_weather", boom)
    monkeypatch.setattr(
        app_module,
        "get_github_activity",
        lambda settings: GitHubActivity("repo", 0, 0, 24, fixed_time),
    )
    app = create_app(settings=Settings())
    app.config.update(TESTING=True)
    with app.test_client() as test_client:
        response = test_client.get("/api/data")
        payload = response.get_json()
        assert payload["weather"] is None
        assert payload["errors"]["weather"] == "weather down"
        # Other sections still succeed.
        assert payload["errors"]["activity"] is None
        assert payload["errors"]["time"] is None
