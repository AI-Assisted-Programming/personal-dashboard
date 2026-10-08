"""Tests for the service layer."""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
import requests

from dashboard.services import (
    DashboardError,
    get_current_time,
    get_github_activity,
    get_weather,
)

from .conftest import FakeResponse, FakeSession


class TestGetCurrentTime:
    def test_returns_time_in_requested_timezone(self):
        now = get_current_time("Europe/Warsaw")
        assert now.tzinfo is not None
        assert now.utcoffset() == dt.timedelta(hours=2) or now.utcoffset() == dt.timedelta(hours=1)

    def test_unknown_timezone_raises(self):
        with pytest.raises(DashboardError):
            get_current_time("Not/AZone")


class TestGetWeather:
    def test_parses_open_meteo_response(self, settings):
        session = FakeSession(
            handler=lambda url, params: {
                "current": {
                    "time": "2026-10-08T09:00",
                    "temperature_2m": 12.3,
                    "apparent_temperature": 10.1,
                    "wind_speed_10m": 15.4,
                    "weather_code": 3,
                }
            }
        )
        weather = get_weather(settings, session=session)

        assert weather.location == "Wrocław, Poland"
        assert weather.temperature_c == pytest.approx(12.3)
        assert weather.apparent_temperature_c == pytest.approx(10.1)
        assert weather.wind_speed_kmh == pytest.approx(15.4)
        assert weather.description == "Overcast"
        assert weather.observed_at.tzinfo is not None
        assert weather.observed_at == dt.datetime(
            2026, 10, 8, 9, 0, tzinfo=ZoneInfo("Europe/Warsaw")
        )

    def test_unknown_weather_code(self, settings):
        session = FakeSession(
            handler=lambda url, params: {
                "current": {
                    "time": "2026-10-08T09:00",
                    "temperature_2m": 1.0,
                    "apparent_temperature": 1.0,
                    "wind_speed_10m": 1.0,
                    "weather_code": 1234,
                }
            }
        )
        weather = get_weather(settings, session=session)
        assert weather.description == "Unknown (1234)"

    def test_http_error_raises_dashboard_error(self, settings):
        session = FakeSession(responses=[FakeResponse({}, status_code=500)])
        with pytest.raises(DashboardError):
            get_weather(settings, session=session)

    def test_malformed_payload_raises_dashboard_error(self, settings):
        session = FakeSession(handler=lambda url, params: {"unexpected": True})
        with pytest.raises(DashboardError):
            get_weather(settings, session=session)

    def test_network_error_raises_dashboard_error(self, settings):
        class Boom(FakeSession):
            def get(self, *args, **kwargs):
                raise requests.ConnectionError("boom")

        with pytest.raises(DashboardError):
            get_weather(settings, session=Boom())


class TestGetGithubActivity:
    def test_counts_issues_and_prs_separately(self, settings):
        def handler(url, params):
            if "/repos/" in url:
                return {"full_name": "OpenHands/OpenHands"}
            if "is:pull-request" in params["q"]:
                return {"total_count": 5}
            return {"total_count": 12}

        session = FakeSession(handler=handler)
        activity = get_github_activity(settings, session=session)

        assert activity.repo == "OpenHands/OpenHands"
        assert activity.pull_requests_opened == 5
        assert activity.issues_opened == 12
        assert activity.window_hours == 24
        search_calls = [c for c in session.calls if "/search/issues" in c["url"]]
        assert len(search_calls) == 2
        assert all("created:>=" in c["params"]["q"] for c in search_calls)
        assert all(
            "is:issue" in c["params"]["q"] or "is:pull-request" in c["params"]["q"]
            for c in search_calls
        )
        assert session.calls[0]["headers"]["Authorization"] == "Bearer test-token"

    def test_renamed_repo_is_resolved(self, settings):
        def handler(url, params):
            if "/repos/" in url:
                return {"full_name": "NewOwner/new-name"}
            return {"total_count": 0}

        session = FakeSession(handler=handler)
        activity = get_github_activity(settings, session=session)
        assert activity.repo == "NewOwner/new-name"
        search_calls = [c for c in session.calls if "/search/issues" in c["url"]]
        assert all("repo:NewOwner/new-name" in c["params"]["q"] for c in search_calls)

    def test_missing_token_omits_authorization(self):
        from dashboard.config import Settings

        settings = Settings(github_token=None)
        session = FakeSession(handler=lambda url, params: {"total_count": 0})
        get_github_activity(settings, session=session)
        assert "Authorization" not in session.calls[0]["headers"]

    def test_api_failure_raises(self, settings):
        def handler(url, params):
            if "/repos/" in url:
                return FakeResponse({}, status_code=404)
            return {"total_count": 0}

        session = FakeSession(handler=handler)
        with pytest.raises(DashboardError):
            get_github_activity(settings, session=session)

    def test_search_failure_raises(self, settings):
        def handler(url, params):
            if "/repos/" in url:
                return {"full_name": "OpenHands/OpenHands"}
            return FakeResponse({}, status_code=403)

        session = FakeSession(handler=handler)
        with pytest.raises(DashboardError):
            get_github_activity(settings, session=session)
