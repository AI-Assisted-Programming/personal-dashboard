"""Service layer that gathers dashboard data from external sources."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import requests

from dashboard.config import Settings

WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


class DashboardError(Exception):
    """Raised when dashboard data cannot be collected."""


@dataclass(frozen=True)
class Weather:
    """Current weather at a location."""

    location: str
    temperature_c: float
    apparent_temperature_c: float
    wind_speed_kmh: float
    description: str
    observed_at: dt.datetime


@dataclass(frozen=True)
class GitHubActivity:
    """Counts of recently opened issues and pull requests for a repository."""

    repo: str
    issues_opened: int
    pull_requests_opened: int
    window_hours: int
    since: dt.datetime


def get_current_time(timezone: str) -> dt.datetime:
    """Return the current time in the given IANA timezone."""
    try:
        tz = ZoneInfo(timezone)
    except Exception as exc:  # noqa: BLE001 - surfaced to the user as a clean error
        raise DashboardError(f"Unknown timezone: {timezone!r}") from exc
    return dt.datetime.now(tz)


def get_weather(settings: Settings, *, session: requests.Session | None = None) -> Weather:
    """Fetch current weather from the Open-Meteo API (no API key required)."""
    http = session or requests
    params = {
        "latitude": settings.weather_latitude,
        "longitude": settings.weather_longitude,
        "current": "temperature_2m,apparent_temperature,wind_speed_10m,weather_code",
        "timezone": settings.timezone,
    }
    try:
        response = http.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=settings.request_timeout,
        )
        response.raise_for_status()
        payload = response.json()
        current = payload["current"]
    except requests.RequestException as exc:
        raise DashboardError(f"Could not fetch weather: {exc}") from exc
    except (KeyError, ValueError) as exc:
        raise DashboardError("Unexpected weather API response") from exc

    code = int(current["weather_code"])
    observed_at = dt.datetime.fromisoformat(current["time"]).replace(
        tzinfo=ZoneInfo(settings.timezone)
    )
    return Weather(
        location=settings.weather_location_name,
        temperature_c=float(current["temperature_2m"]),
        apparent_temperature_c=float(current["apparent_temperature"]),
        wind_speed_kmh=float(current["wind_speed_10m"]),
        description=WEATHER_CODES.get(code, f"Unknown ({code})"),
        observed_at=observed_at,
    )


def _github_headers(settings: Settings) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "personal-dashboard",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def _resolve_repo(http, settings: Settings, headers: dict[str, str], repo: str) -> str:
    """Return the canonical ``owner/name`` for ``repo``.

    Repositories can be renamed; the search API rejects the old name, while the
    repository endpoint responds with a redirect to the new location. Following
    that redirect keeps the dashboard working across renames.
    """
    try:
        response = http.get(
            f"{settings.github_api_url}/repos/{repo}",
            headers=headers,
            timeout=settings.request_timeout,
        )
        response.raise_for_status()
        return response.json().get("full_name") or repo
    except (requests.RequestException, ValueError, AttributeError) as exc:
        raise DashboardError(f"Could not resolve repository {repo!r}: {exc}") from exc


def get_github_activity(
    settings: Settings, *, session: requests.Session | None = None
) -> GitHubActivity:
    """Count issues and pull requests opened in the last 24 hours.

    Both counts come from the search API, which requires an explicit
    ``is:issue`` / ``is:pull-request`` qualifier.
    """
    http = session or requests
    now = get_current_time("UTC")
    since = now - dt.timedelta(hours=24)
    since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")

    headers = _github_headers(settings)
    repo = _resolve_repo(http, settings, headers, settings.github_repo)
    base_query = f"repo:{repo} created:>={since_str}"

    def count(qualifier: str) -> int:
        params = {"q": f"{base_query} {qualifier}", "per_page": 1}
        try:
            response = http.get(
                f"{settings.github_api_url}/search/issues",
                params=params,
                headers=headers,
                timeout=settings.request_timeout,
            )
            response.raise_for_status()
            return int(response.json()["total_count"])
        except requests.RequestException as exc:
            raise DashboardError(f"Could not fetch GitHub activity: {exc}") from exc
        except (KeyError, ValueError) as exc:
            raise DashboardError("Unexpected GitHub API response") from exc

    return GitHubActivity(
        repo=repo,
        issues_opened=count("is:issue"),
        pull_requests_opened=count("is:pull-request"),
        window_hours=24,
        since=since,
    )
