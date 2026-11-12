import io
import json
import urllib.error

import pytest

from route import google
from route.errors import RouteError


def failing(code, body=b""):
    def urlopen(request, timeout):
        urlopen.calls += 1
        raise urllib.error.HTTPError(google.URL, code, "reason", {}, io.BytesIO(body))
    urlopen.calls = 0
    return urlopen


def test_quota_is_not_retried(monkeypatch):
    urlopen = failing(429, b'{"error": {"code": 429, "status": "RESOURCE_EXHAUSTED"}}')
    monkeypatch.setattr(google.urllib.request, "urlopen", urlopen)
    with pytest.raises(RouteError, match="Google quota reached"):
        google.compute_routes("k", {})
    assert urlopen.calls == 1


def test_error_message_is_passed_on(monkeypatch):
    body = json.dumps({"error": {"code": 400, "message": "Invalid field mask"}}).encode()
    monkeypatch.setattr(google.urllib.request, "urlopen", failing(400, body))
    with pytest.raises(RouteError, match="answered 400: Invalid field mask"):
        google.compute_routes("k", {})


def test_non_json_error(monkeypatch):
    monkeypatch.setattr(google.urllib.request, "urlopen", failing(502, b"<html>"))
    with pytest.raises(RouteError, match="answered 502: reason"):
        google.compute_routes("k", {})


def test_headers(monkeypatch):
    seen = {}

    def urlopen(request, timeout):
        seen.update(request.headers)
        return io.BytesIO(b"{}")

    monkeypatch.setattr(google.urllib.request, "urlopen", urlopen)
    assert google.compute_routes("secret", {}) == {}
    assert seen["X-goog-api-key"] == "secret"
    assert seen["X-goog-fieldmask"] == google.FIELD_MASK
