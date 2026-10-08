"""Flask application factory for the personal dashboard."""

from __future__ import annotations

import logging

from flask import Flask, jsonify, render_template

from dashboard.config import Settings
from dashboard.services import (
    DashboardError,
    get_current_time,
    get_github_activity,
    get_weather,
)

logger = logging.getLogger(__name__)


def collect_dashboard_data(settings: Settings) -> dict:
    """Collect all dashboard sections, isolating failures per section.

    A failure in one section (for example, a network error) does not prevent
    the remaining sections from being displayed.
    """

    def safe(fn, *args):
        try:
            return fn(*args), None
        except DashboardError as exc:
            logger.warning("Dashboard section failed: %s", exc)
            return None, str(exc)

    current_time, time_error = safe(get_current_time, settings.timezone)
    weather, weather_error = safe(get_weather, settings)
    activity, activity_error = safe(get_github_activity, settings)

    return {
        "time": current_time,
        "weather": weather,
        "activity": activity,
        "errors": {
            "time": time_error,
            "weather": weather_error,
            "activity": activity_error,
        },
        "settings": settings,
    }


def create_app(settings: Settings | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config["SETTINGS"] = settings or Settings.from_env()

    @app.route("/")
    def index():
        data = collect_dashboard_data(app.config["SETTINGS"])
        return render_template("index.html", **data)

    @app.route("/api/data")
    def api_data():
        data = collect_dashboard_data(app.config["SETTINGS"])
        return jsonify(
            {
                "time": data["time"].isoformat() if data["time"] else None,
                "weather": _weather_dict(data["weather"]),
                "activity": _activity_dict(data["activity"]),
                "errors": data["errors"],
            }
        )

    @app.route("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    return app


def _weather_dict(weather) -> dict | None:
    if weather is None:
        return None
    return {
        "location": weather.location,
        "temperature_c": weather.temperature_c,
        "apparent_temperature_c": weather.apparent_temperature_c,
        "wind_speed_kmh": weather.wind_speed_kmh,
        "description": weather.description,
        "observed_at": weather.observed_at.isoformat(),
    }


def _activity_dict(activity) -> dict | None:
    if activity is None:
        return None
    return {
        "repo": activity.repo,
        "issues_opened": activity.issues_opened,
        "pull_requests_opened": activity.pull_requests_opened,
        "window_hours": activity.window_hours,
        "since": activity.since.isoformat(),
    }


def run() -> None:
    """Entry point for the ``personal-dashboard`` console script."""
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    run()
