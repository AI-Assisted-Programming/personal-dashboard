"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from dashboard.config import Settings


class FakeResponse:
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"status {self.status_code}")


class FakeSession:
    """Records requests and returns queued responses.

    Provide either a list of responses (returned in order) or a single
    callable that maps ``(url, params)`` to a payload.
    """

    def __init__(self, responses=None, handler=None):
        self._responses = list(responses) if responses is not None else None
        self._handler = handler
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        if self._handler is not None:
            payload = self._handler(url, params)
            if isinstance(payload, FakeResponse):
                return payload
            return FakeResponse(payload)
        response = self._responses.pop(0)
        return response


@pytest.fixture
def settings() -> Settings:
    return Settings(github_token="test-token")


@pytest.fixture
def fake_session_factory():
    return FakeSession
