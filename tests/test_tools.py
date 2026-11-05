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
