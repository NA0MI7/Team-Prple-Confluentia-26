"""Pytest integration for fuzz invariant verification."""
import pytest
from scripts.fuzz_engine import run_fuzz_campaign


def test_fuzz_invariants_campaign():
    # Run 1,000 fast invariant checks during automated test runs
    success = run_fuzz_campaign(target_steps=1000, seed=123)
    assert success, "Invariant violations detected during fuzz testing"
