"""
Tests for simcore engine and world generator.
Phase 1: Determinism, basic mechanics, invariants.
"""
import sys
import os
import json
import copy

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simcore.engine import Engine, state_hash
from simcore.world import generate, validate_oracle, get_all_task_ids, TASK_CONFIGS


# ======================== DETERMINISM TESTS ========================

def test_same_seed_same_world():
    """Same (task_id, seed) gives identical world."""
    for task_id in get_all_task_ids():
        w1 = generate(task_id, 42)
        w2 = generate(task_id, 42)
        assert w1["prices"] == w2["prices"], f"{task_id}: prices differ"
        assert w1["events"] == w2["events"], f"{task_id}: events differ"
        assert w1["initial_state"] == w2["initial_state"], f"{task_id}: initial_state differs"
        assert w1["cfg"] == w2["cfg"], f"{task_id}: cfg differs"
    print("PASS: test_same_seed_same_world")


def test_different_seeds_differ():
    """Different seeds give different worlds."""
    for task_id in get_all_task_ids():
        w1 = generate(task_id, 0)
        w2 = generate(task_id, 1)
        # At least prices should differ
        assert w1["prices"] != w2["prices"], f"{task_id}: seeds 0 and 1 gave same prices"
    print("PASS: test_different_seeds_differ")


def test_state_hash_determinism():
    """Same seed gives same initial state hash."""
    for task_id in get_all_task_ids():
        w1 = generate(task_id, 7)
        w2 = generate(task_id, 7)
        h1 = state_hash(w1["initial_state"])
        h2 = state_hash(w2["initial_state"])
        assert h1 == h2, f"{task_id}: hash mismatch {h1} != {h2}"
    print("PASS: test_state_hash_determinism")


def test_replay_determinism():
    """Replaying oracle actions gives identical result."""
    for task_id in get_all_task_ids():
        world = generate(task_id, 42)

        # Run 1
        eng1 = Engine(world)
        for name, args in world["oracle_actions"]:
            getattr(eng1, name)(**args)
        h1 = eng1.get_state_hash()
        nw1 = eng1.compute_net_worth()

        # Run 2
        eng2 = Engine(world)
        for name, args in world["oracle_actions"]:
            getattr(eng2, name)(**args)
        h2 = eng2.get_state_hash()
        nw2 = eng2.compute_net_worth()

        assert h1 == h2, f"{task_id}: replay hash mismatch"
        assert nw1 == nw2, f"{task_id}: replay net worth mismatch"
    print("PASS: test_replay_determinism")


# ======================== BASIC MECHANIC TESTS ========================

def test_plant_and_harvest():
    """Basic plant->wait->harvest flow."""
    world = generate("farm_basic", 0)
    eng = Engine(world)

    # Plant wheat on plot 0
    text, err, done = eng.plant(0, "wheat")
    assert not err, f"Plant failed: {text}"

    # Can't plant on occupied plot
    text, err, done = eng.plant(0, "wheat")
    assert err, "Should reject planting on occupied plot"

    # Advance to harvest
    grow_days = world["cfg"]["crops"]["wheat"]["grow_days"]
    eng.advance_days(grow_days)

    # Harvest
    text, err, done = eng.harvest(0)
    assert not err, f"Harvest failed: {text}"

    # Plot should be empty now
    state = eng.get_state()
    assert state["plots"]["0"]["crop"] is None
    assert len(state["inventory"]) > 0
    print("PASS: test_plant_and_harvest")


def test_sell_with_slippage():
    """Selling applies slippage correctly."""
    world = generate("farm_basic", 0)
    eng = Engine(world)

    # Plant, grow, harvest
    eng.plant(0, "wheat")
    eng.advance_days(world["cfg"]["crops"]["wheat"]["grow_days"])
    eng.harvest(0)

    state = eng.get_state()
    qty = sum(lot["qty"] for lot in state["inventory"])
    cash_before = state["cash"]

    # Sell all
    text, err, done = eng.sell("wheat", qty)
    assert not err, f"Sell failed: {text}"

    state = eng.get_state()
    assert state["cash"] > cash_before, "Cash should increase after selling"
    assert sum(lot["qty"] for lot in state["inventory"]) == 0, "Inventory should be empty"
    print("PASS: test_sell_with_slippage")


def test_sell_more_than_owned():
    """Selling more than owned returns error."""
    world = generate("farm_basic", 0)
    eng = Engine(world)
    text, err, done = eng.sell("wheat", 100)
    assert err, "Should reject selling more than owned"
    print("PASS: test_sell_more_than_owned")


def test_land_tax():
    """Land tax reduces cash each day."""
    world = generate("farm_basic", 0)
    eng = Engine(world)
    cash_before = eng.get_state()["cash"]
    eng.advance_days(1)
    cash_after = eng.get_state()["cash"]
    expected_tax = world["cfg"]["land_tax"] * world["cfg"]["n_plots"]
    assert cash_after == cash_before - expected_tax, \
        f"Tax not applied correctly: {cash_before} - {expected_tax} != {cash_after}"
    print("PASS: test_land_tax")


def test_noop_negative_gain():
    """Doing nothing (just finishing) should give non-positive gain."""
    for task_id in get_all_task_ids():
        world = generate(task_id, 42)
        eng = Engine(world)
        eng.finish()
        nw = eng.compute_net_worth()
        gain = nw - world["cfg"]["start_cash"]
        assert gain <= 0, f"{task_id}: no-op gain should be <= 0, got {gain}"
    print("PASS: test_noop_negative_gain")


def test_noop_score_zero():
    """No-op score should be <= 0.05."""
    for task_id in get_all_task_ids():
        oracle_gain, world = validate_oracle(task_id, 42)
        eng = Engine(world)
        eng.finish()
        score = eng.compute_score(oracle_gain)
        assert score["total"] <= 0.05, \
            f"{task_id}: no-op total={score['total']}, should be <= 0.05"
    print("PASS: test_noop_score_zero")


# ======================== LOAN TESTS ========================

def test_loans():
    """Loan mechanics work correctly."""
    world = generate("farm_credit", 0)
    eng = Engine(world)

    # Take loan
    text, err, done = eng.take_loan(5000)
    assert not err, f"Loan failed: {text}"
    state = eng.get_state()
    assert state["debt"] == 5000
    assert state["cash"] == world["cfg"]["start_cash"] + 5000

    # Over limit
    text, err, done = eng.take_loan(100000)
    assert err, "Should reject over-limit loan"

    # Repay
    text, err, done = eng.repay(3000)
    assert not err, f"Repay failed: {text}"
    state = eng.get_state()
    assert state["debt"] == 2000

    # Can't repay more than cash
    text, err, done = eng.repay(999999)
    assert err, "Should reject repay > cash"

    print("PASS: test_loans")


def test_loans_unavailable_on_basic():
    """Loans should be unavailable on tasks without loans."""
    world = generate("farm_basic", 0)
    eng = Engine(world)
    text, err, done = eng.take_loan(1000)
    assert err, "Loans should not be available on farm_basic"
    print("PASS: test_loans_unavailable_on_basic")


# ======================== SPOILAGE TESTS ========================

def test_spoilage():
    """Items spoil after spoil_days."""
    world = generate("farm_seasons", 0)
    eng = Engine(world)

    # Plant and harvest a tomato (spoil_days=5)
    eng.plant(0, "tomato")
    eng.advance_days(3)  # grow_days for tomato
    eng.harvest(0)

    # Advance past spoil deadline
    eng.advance_days(6)  # should spoil
    state = eng.get_state()
    tomato_qty = sum(lot["qty"] for lot in state["inventory"] if lot["crop"] == "tomato")
    assert tomato_qty == 0, f"Tomatoes should have spoiled, but {tomato_qty} remain"
    print("PASS: test_spoilage")


# ======================== STORAGE TESTS ========================

def test_storage_cap():
    """Storage cap limits inventory."""
    world = generate("farm_crash", 0)
    eng = Engine(world)
    # farm_crash has storage_cap=50
    # Try to fill up storage
    cap = world["cfg"]["storage_cap"]

    # Plant and harvest repeatedly to fill storage
    crops = sorted(world["cfg"]["crops"].keys())
    # Use whichever crop gives most yield
    crop_name = max(crops, key=lambda c: world["cfg"]["crops"][c]["yield_units"])
    ccfg = world["cfg"]["crops"][crop_name]

    total_harvested = 0
    for cycle in range(10):
        if total_harvested >= cap:
            break
        state = eng.get_state()
        if eng.is_done():
            break
        # Plant on all empty plots
        for pid in sorted(state["plots"].keys(), key=lambda x: int(x)):
            if state["plots"][pid]["crop"] is None and state["cash"] >= ccfg["seed_cost"]:
                eng.plant(int(pid), crop_name)
        # Advance to harvest
        eng.advance_days(min(7, ccfg["grow_days"]))
        if eng.is_done():
            break
        # Harvest
        state = eng.get_state()
        for pid in sorted(state["plots"].keys(), key=lambda x: int(x)):
            plot = state["plots"][pid]
            if plot["crop"] is not None:
                if state["day"] >= plot["planted_day"] + ccfg["grow_days"]:
                    eng.harvest(int(pid))
        state = eng.get_state()
        total_harvested = sum(lot["qty"] for lot in state["inventory"])

    # Verify we don't exceed cap
    state = eng.get_state()
    total = sum(lot["qty"] for lot in state["inventory"])
    assert total <= cap, f"Storage exceeded cap: {total} > {cap}"
    print("PASS: test_storage_cap")


# ======================== ADVANCE_DAYS TESTS ========================

def test_advance_days_bounds():
    """advance_days rejects invalid values."""
    world = generate("farm_basic", 0)
    eng = Engine(world)

    text, err, done = eng.advance_days(0)
    assert err, "Should reject n=0"

    text, err, done = eng.advance_days(8)
    assert err, "Should reject n=8"

    text, err, done = eng.advance_days(-1)
    assert err, "Should reject n=-1"

    print("PASS: test_advance_days_bounds")


def test_game_over_at_horizon():
    """Game ends when day reaches horizon."""
    world = generate("farm_basic", 0)
    eng = Engine(world)
    horizon = world["cfg"]["horizon"]

    # Advance to end
    for _ in range(horizon):
        if eng.is_done():
            break
        eng.advance_days(1)

    assert eng.is_done(), "Game should be over at horizon"
    # Further actions should return game over
    text, err, done = eng.plant(0, "wheat")
    assert err and done, "Actions after game over should return error+done"
    print("PASS: test_game_over_at_horizon")


# ======================== FORECAST TESTS ========================

def test_forecast_determinism():
    """Repeated get_forecast on same day returns identical values."""
    world = generate("farm_seasons", 0)
    eng = Engine(world)
    text1, _, _ = eng.get_forecast()
    text2, _, _ = eng.get_forecast()
    assert text1 == text2, "Forecast should be identical on repeated calls"
    print("PASS: test_forecast_determinism")


# ======================== ORACLE TESTS ========================

def test_oracle_positive_gain():
    """Oracle achieves positive gain on all tasks."""
    for task_id in get_all_task_ids():
        for seed in [0, 7, 42]:
            oracle_gain, world = validate_oracle(task_id, seed)
            assert oracle_gain > 0, \
                f"{task_id} seed={seed}: oracle_gain={oracle_gain} should be > 0"
    print("PASS: test_oracle_positive_gain")


def test_oracle_score_high():
    """Oracle achieves >= 0.95 total score on all tasks."""
    for task_id in get_all_task_ids():
        for seed in [0, 7, 42]:
            oracle_gain, world = validate_oracle(task_id, seed)
            eng = Engine(world)
            for name, args in world["oracle_actions"]:
                getattr(eng, name)(**args)
            if not eng.is_done():
                eng.finish()
            score = eng.compute_score(oracle_gain)
            assert score["total"] >= 0.95, \
                f"{task_id} seed={seed}: oracle total={score['total']}, need >= 0.95"
    print("PASS: test_oracle_score_high")


# ======================== MONEY INVARIANT TESTS ========================

def test_money_always_int():
    """Cash, debt are always integers throughout oracle play."""
    for task_id in get_all_task_ids():
        world = generate(task_id, 42)
        eng = Engine(world)
        for name, args in world["oracle_actions"]:
            getattr(eng, name)(**args)
            state = eng.get_state()
            assert isinstance(state["cash"], int), f"Cash not int: {state['cash']}"
            assert isinstance(state["debt"], int), f"Debt not int: {state['debt']}"
            assert state["cash"] >= 0, f"Cash negative: {state['cash']}"
            assert state["debt"] >= 0, f"Debt negative: {state['debt']}"
    print("PASS: test_money_always_int")


# ======================== ADVERSARIAL INPUT TESTS ========================

def test_invalid_inputs_never_raise():
    """Malformed inputs return errors, never raise."""
    world = generate("farm_basic", 0)
    eng = Engine(world)

    bad_calls = [
        ("plant", {"plot_id": -1, "crop": "wheat"}),
        ("plant", {"plot_id": 999, "crop": "wheat"}),
        ("plant", {"plot_id": 0, "crop": "unicorn"}),
        ("harvest", {"plot_id": -1}),
        ("harvest", {"plot_id": 999}),
        ("sell", {"crop": "wheat", "quantity": 0}),
        ("sell", {"crop": "wheat", "quantity": -5}),
        ("sell", {"crop": "wheat", "quantity": 10**9}),
        ("sell", {"crop": "nonexistent", "quantity": 1}),
        ("advance_days", {"n": 0}),
        ("advance_days", {"n": -1}),
        ("advance_days", {"n": 100}),
        ("take_loan", {"amount_cents": -1}),
        ("take_loan", {"amount_cents": 10**9}),
        ("repay", {"amount_cents": -1}),
        ("repay", {"amount_cents": 0}),
    ]

    for name, args in bad_calls:
        try:
            text, err, done = getattr(eng, name)(**args)
            # Should be an error, not a crash
        except Exception as e:
            assert False, f"{name}({args}) raised {type(e).__name__}: {e}"

    print("PASS: test_invalid_inputs_never_raise")


def test_double_finish():
    """Double finish doesn't crash."""
    world = generate("farm_basic", 0)
    eng = Engine(world)
    eng.finish()
    text, err, done = eng.finish()
    assert err or done, "Second finish should indicate done"
    print("PASS: test_double_finish")


def test_actions_after_game_over():
    """Actions after game over don't crash."""
    world = generate("farm_basic", 0)
    eng = Engine(world)
    eng.finish()

    actions = [
        ("get_status", {}),
        ("get_market", {"history_days": 0}),
        ("get_forecast", {}),
        ("get_news", {}),
        ("plant", {"plot_id": 0, "crop": "wheat"}),
        ("harvest", {"plot_id": 0}),
        ("sell", {"crop": "wheat", "quantity": 1}),
        ("advance_days", {"n": 1}),
        ("finish", {}),
    ]
    for name, args in actions:
        try:
            text, err, done = getattr(eng, name)(**args)
        except Exception as e:
            assert False, f"{name}({args}) after game over raised: {e}"
    print("PASS: test_actions_after_game_over")


# ======================== FUZZ TESTS ========================

def test_fuzz_random_actions():
    """1000 random/malformed tool calls never raise."""
    import random as stdlib_random
    rng = stdlib_random.Random(12345)

    for task_id in get_all_task_ids():
        world = generate(task_id, 0)
        eng = Engine(world)

        crops = sorted(world["cfg"]["crops"].keys()) + ["invalid", "", "🌾"]
        plots = list(range(-2, world["cfg"]["n_plots"] + 3))

        for _ in range(1000):
            action = rng.choice([
                "plant", "harvest", "sell", "take_loan", "repay",
                "advance_days", "get_status", "get_market", "get_forecast",
                "get_news", "finish"
            ])
            try:
                if action == "plant":
                    eng.plant(rng.choice(plots), rng.choice(crops))
                elif action == "harvest":
                    eng.harvest(rng.choice(plots))
                elif action == "sell":
                    eng.sell(rng.choice(crops), rng.choice([-10, 0, 1, 5, 10**9]))
                elif action == "take_loan":
                    eng.take_loan(rng.choice([-100, 0, 1, 5000, 10**9]))
                elif action == "repay":
                    eng.repay(rng.choice([-100, 0, 1, 5000, 10**9]))
                elif action == "advance_days":
                    eng.advance_days(rng.choice([-1, 0, 1, 3, 7, 100, 10**9]))
                elif action == "get_status":
                    eng.get_status()
                elif action == "get_market":
                    eng.get_market(rng.choice([-1, 0, 3, 7, 100]))
                elif action == "get_forecast":
                    eng.get_forecast()
                elif action == "get_news":
                    eng.get_news()
                elif action == "finish":
                    eng.finish()
            except Exception as e:
                assert False, f"Fuzz: {task_id} {action} raised {e}"

    print("PASS: test_fuzz_random_actions")


# ======================== RUN ALL ========================

if __name__ == "__main__":
    tests = [
        test_same_seed_same_world,
        test_different_seeds_differ,
        test_state_hash_determinism,
        test_replay_determinism,
        test_plant_and_harvest,
        test_sell_with_slippage,
        test_sell_more_than_owned,
        test_land_tax,
        test_noop_negative_gain,
        test_noop_score_zero,
        test_loans,
        test_loans_unavailable_on_basic,
        test_spoilage,
        test_storage_cap,
        test_advance_days_bounds,
        test_game_over_at_horizon,
        test_forecast_determinism,
        test_oracle_positive_gain,
        test_oracle_score_high,
        test_money_always_int,
        test_invalid_inputs_never_raise,
        test_double_finish,
        test_actions_after_game_over,
        test_fuzz_random_actions,
    ]

    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed > 0:
        sys.exit(1)
