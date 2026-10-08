"""Tests for configuration loading."""

from __future__ import annotations

from dashboard.config import WROCLAW_LATITUDE, WROCLAW_LONGITUDE, Settings


def test_defaults():
    settings = Settings.from_env(environ={})
    assert settings.github_token is None
    assert settings.github_repo == "OpenHands/OpenHands"
    assert settings.weather_latitude == WROCLAW_LATITUDE
    assert settings.weather_longitude == WROCLAW_LONGITUDE
    assert settings.timezone == "Europe/Warsaw"


def test_env_overrides():
    settings = Settings.from_env(
        environ={
            "GITHUB_TOKEN": "abc",
            "DASHBOARD_GITHUB_REPO": "owner/repo",
            "DASHBOARD_WEATHER_LATITUDE": "1.5",
            "DASHBOARD_WEATHER_LONGITUDE": "2.5",
            "DASHBOARD_TIMEZONE": "UTC",
        }
    )
    assert settings.github_token == "abc"
    assert settings.github_repo == "owner/repo"
    assert settings.weather_latitude == 1.5
    assert settings.weather_longitude == 2.5
    assert settings.timezone == "UTC"


def test_empty_token_becomes_none():
    settings = Settings.from_env(environ={"GITHUB_TOKEN": ""})
    assert settings.github_token is None
