"""Pytest integration for Red Team Attack & Defense Suite."""
import pytest
from scripts.red_team import run_red_team_suite


def test_red_team_all_defended():
    all_ok, results = run_red_team_suite()
    assert all_ok, f"Vulnerabilities found in red team suite: {results}"
    assert len(results) == 7, "All 7 attack vectors must be tested"
    for r in results:
        assert r["success"], f"Attack vector failed defense: {r['attack']}"
