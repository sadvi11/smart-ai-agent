"""Tool-level tests. The model picks tool inputs, so inputs are untrusted."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from tools import calculate


@pytest.mark.parametrize("expr,expected", [
    ("45*40", "Result: 1800"),
    ("2 + 3 * 4", "Result: 14"),
    ("(2 + 3) * 4", "Result: 20"),
    ("10 / 4", "Result: 2.5"),
    ("-5 + 2", "Result: -3"),
])
def test_calculate_valid(expr, expected):
    assert calculate(expr) == expected


@pytest.mark.parametrize("expr", [
    "__import__('os').system('id')",
    "open('/etc/passwd')",
    "().__class__",
    "1; 2",
    "abc",
    "",
    "   ",
])
def test_calculate_rejects_non_arithmetic(expr):
    assert calculate(expr).startswith("Invalid")


def test_calculate_rejects_exponent_dos_quickly():
    start = time.monotonic()
    result = calculate("9**9**9")
    assert result.startswith("Invalid")
    assert time.monotonic() - start < 1


def test_calculate_division_by_zero():
    assert "division by zero" in calculate("1/0")


def test_calculate_rejects_oversized_input():
    assert "too long" in calculate("1+" * 150 + "1")


def test_calculate_rejects_non_string():
    assert calculate(None).startswith("Invalid")


# ── get_weather ──────────────────────────────────────────────────────
from unittest.mock import MagicMock, patch

import requests

import tools


def _ok_response():
    r = MagicMock()
    r.raise_for_status.return_value = None
    r.json.return_value = {"current": {"temp_c": 3, "condition": {"text": "Cloudy"}, "humidity": 50}}
    return r


def test_weather_uses_https_params_and_timeout(monkeypatch):
    monkeypatch.setenv("WEATHER_API_KEY", "test-value")
    with patch.object(tools.requests, "get", return_value=_ok_response()) as g:
        out = tools.get_weather("Calgary")
    assert "3°C" in out
    args, kwargs = g.call_args
    assert args[0].startswith("https://")
    assert kwargs["params"]["q"] == "Calgary"
    assert kwargs["timeout"] > 0


def test_weather_without_key_does_not_call_upstream(monkeypatch):
    monkeypatch.delenv("WEATHER_API_KEY", raising=False)
    with patch.object(tools.requests, "get") as g:
        assert "not configured" in tools.get_weather("Calgary")
    assert not g.called


def test_weather_error_does_not_leak_key(monkeypatch):
    monkeypatch.setenv("WEATHER_API_KEY", "super-sensitive-value")
    boom = requests.ConnectionError("failed for url ...key=super-sensitive-value")
    with patch.object(tools.requests, "get", side_effect=boom):
        out = tools.get_weather("Calgary")
    assert "super-sensitive-value" not in out


def test_weather_http_error_reports_status_only(monkeypatch):
    monkeypatch.setenv("WEATHER_API_KEY", "super-sensitive-value")
    resp = MagicMock(status_code=401)
    err = requests.HTTPError("401 for url key=super-sensitive-value", response=resp)
    bad = MagicMock()
    bad.raise_for_status.side_effect = err
    with patch.object(tools.requests, "get", return_value=bad):
        out = tools.get_weather("Calgary")
    assert "401" in out and "super-sensitive-value" not in out
