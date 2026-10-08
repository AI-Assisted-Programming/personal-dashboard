"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

# Coordinates for Wrocław, Poland.
WROCLAW_LATITUDE = 51.1079
WROCLAW_LONGITUDE = 17.0385


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the dashboard."""

    github_token: str | None = None
    github_repo: str = "OpenHands/OpenHands"
    github_api_url: str = "https://api.github.com"
    weather_latitude: float = WROCLAW_LATITUDE
    weather_longitude: float = WROCLAW_LONGITUDE
    weather_location_name: str = "Wrocław, Poland"
    timezone: str = "Europe/Warsaw"
    request_timeout: float = 10.0

    @classmethod
    def from_env(cls, environ: dict[str, str] | None = None) -> Settings:
        """Build settings from ``environ`` (defaults to ``os.environ``)."""
        environ = os.environ if environ is None else environ
        return cls(
            github_token=environ.get("GITHUB_TOKEN") or None,
            github_repo=environ.get("DASHBOARD_GITHUB_REPO", "OpenHands/OpenHands"),
            github_api_url=environ.get("DASHBOARD_GITHUB_API_URL", "https://api.github.com"),
            weather_latitude=float(environ.get("DASHBOARD_WEATHER_LATITUDE", WROCLAW_LATITUDE)),
            weather_longitude=float(environ.get("DASHBOARD_WEATHER_LONGITUDE", WROCLAW_LONGITUDE)),
            weather_location_name=environ.get("DASHBOARD_WEATHER_LOCATION_NAME", "Wrocław, Poland"),
            timezone=environ.get("DASHBOARD_TIMEZONE", "Europe/Warsaw"),
            request_timeout=float(environ.get("DASHBOARD_REQUEST_TIMEOUT", "10.0")),
        )
