# Personal Dashboard

A small Flask app that shows at a glance:

1. The current time (Europe/Warsaw, configurable)
2. The current weather in Wrocław, Poland (via the keyless [Open-Meteo](https://open-meteo.com/) API)
3. The number of issues and pull requests opened on the
   [`OpenHands/OpenHands`](https://github.com/OpenHands/OpenHands) repository
   in the last 24 hours (via the GitHub search API). The dashboard resolves the
   repository's current name, so it keeps working across renames
   (it was previously `All-Hands-AI/OpenHands`).

Each section fails independently: if one data source is unavailable, the rest of
the dashboard still renders and the failing section shows an explanatory message.

## Requirements

- Python 3.10+
- (Optional but recommended) a GitHub personal access token to avoid the low
  anonymous search rate limit

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running

```bash
export GITHUB_TOKEN=ghp_...        # optional, recommended
python -m dashboard                # or: personal-dashboard
```

Then open <http://localhost:5000>.

### Endpoints

| Path        | Description                              |
| ----------- | ---------------------------------------- |
| `/`         | HTML dashboard                           |
| `/api/data` | JSON snapshot of all dashboard sections  |
| `/healthz`  | Liveness probe                           |

## Configuration

All settings have sensible defaults and can be overridden via environment
variables:

| Variable                       | Default                  |
| ------------------------------ | ------------------------ |
| `GITHUB_TOKEN`                 | _unset_                  |
| `DASHBOARD_GITHUB_REPO`        | `OpenHands/OpenHands` |
| `DASHBOARD_GITHUB_API_URL`     | `https://api.github.com` |
| `DASHBOARD_WEATHER_LATITUDE`   | `51.1079` (Wrocław)      |
| `DASHBOARD_WEATHER_LONGITUDE`  | `17.0385` (Wrocław)      |
| `DASHBOARD_WEATHER_LOCATION_NAME` | `Wrocław, Poland`     |
| `DASHBOARD_TIMEZONE`           | `Europe/Warsaw`          |
| `DASHBOARD_REQUEST_TIMEOUT`    | `10.0`                   |

## Development

```bash
ruff check .          # lint
ruff format .         # format
pytest -q             # tests
pre-commit install    # enable git hooks
pre-commit run --all-files
```

Continuous integration (`.github/workflows/ci.yml`) runs ruff and pytest on
every push and pull request.
