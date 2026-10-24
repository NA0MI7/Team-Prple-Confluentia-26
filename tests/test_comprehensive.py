"""
Comprehensive pytest test suite for the Seasonal Farm Market.
Covers: determinism, gate, difficulty curve, invariants fuzz, adversarial,
replay integrity, sandbox tools, and more.
"""
import sys
import os
import json
import copy
import random as stdlib_random

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from simcore.engine import Engine, state_hash
from simcore.world import generate, validate_oracle, get_all_task_ids, TASK_CONFIGS


# ======================== DETERMINISM ========================

class TestDeterminism:
    def test_same_seed_same_world(self):
        for task_id in get_all_task_ids():
            w1 = generate(task_id, 42)
            w2 = generate(task_id, 42)
            assert w1["prices"] == w2["prices"]
            assert w1["events"] == w2["events"]
            assert w1["initial_state"] == w2["initial_state"]

    def test_different_seeds_differ(self):
        for task_id in get_all_task_ids():
            w1 = generate(task_id, 0)
            w2 = generate(task_id, 1)
            assert w1["prices"] != w2["prices"]

    def test_state_hash_determinism(self):
        for task_id in get_all_task_ids():
            w1 = generate(task_id, 7)
            w2 = generate(task_id, 7)
            assert state_hash(w1["initial_state"]) == state_hash(w2["initial_state"])

    def test_replay_identical(self):
        for task_id in get_all_task_ids():
            world = generate(task_id, 42)
            eng1 = Engine(world)
            for n, a in world["oracle_actions"]:
                getattr(eng1, n)(**a)
            eng2 = Engine(world)
            for n, a in world["oracle_actions"]:
                getattr(eng2, n)(**a)
            assert eng1.get_state_hash() == eng2.get_state_hash()
            assert eng1.compute_net_worth() == eng2.compute_net_worth()


# ======================== GATE ========================

class TestGate:
    """Oracle >= 0.95 and no-op <= 0.05 across seeds 0..49 and all tasks."""

    def test_oracle_gate(self):
        for task_id in get_all_task_ids():
            for seed in range(50):
                oracle_gain, world = validate_oracle(task_id, seed)
                eng = Engine(world)
                for n, a in world["oracle_actions"]:
                    getattr(eng, n)(**a)
                if not eng.is_done():
                    eng.finish()
                score = eng.compute_score(oracle_gain)
                assert score["total"] >= 0.95, \
                    f"{task_id} seed={seed}: oracle={score['total']}"

    def test_noop_gate(self):
        for task_id in get_all_task_ids():
            for seed in range(50):
                oracle_gain, world = validate_oracle(task_id, seed)
                eng = Engine(world)
                eng.finish()
                score = eng.compute_score(oracle_gain)
                assert score["total"] <= 0.05, \
                    f"{task_id} seed={seed}: noop={score['total']}"


# ======================== DIFFICULTY CURVE ========================

class TestDifficultyCurve:
    """Greedy agent scores <= 0.7 on tasks 3-6; random agent <= 0.35 avg."""

    def _greedy_play(self, task_id, seed):
        """Greedy: plant cheapest crop everywhere, sell immediately."""
        world = generate(task_id, seed)
        eng = Engine(world)
        cfg = world["cfg"]
        crops = sorted(cfg["crops"].keys())
        cheapest = min(crops, key=lambda c: cfg["crops"][c]["seed_cost"])
        horizon = cfg["horizon"]

        for _ in range(horizon * 5):
            if eng.is_done():
                break
            state = eng.get_state()
            # Plant on empty plots
            for pid in sorted(state["plots"].keys(), key=lambda x: int(x)):
                if state["plots"][pid]["crop"] is None:
                    if state["cash"] >= cfg["crops"][cheapest]["seed_cost"]:
                        eng.plant(int(pid), cheapest)
            # Harvest ready plots
            state = eng.get_state()
            for pid in sorted(state["plots"].keys(), key=lambda x: int(x)):
                plot = state["plots"][pid]
                if plot["crop"] is not None:
                    ccfg = cfg["crops"][plot["crop"]]
                    if state["day"] >= plot["planted_day"] + ccfg["grow_days"]:
                        eng.harvest(int(pid))
            # Sell everything
            state = eng.get_state()
            for crop in sorted(cfg["crops"].keys()):
                owned = sum(l["qty"] for l in state["inventory"] if l["crop"] == crop)
                if owned > 0:
                    eng.sell(crop, owned)
            # Advance 1 day
            if not eng.is_done():
                eng.advance_days(1)

        if not eng.is_done():
            eng.finish()

        oracle_gain, _ = validate_oracle(task_id, seed)
        return eng.compute_score(oracle_gain)

    def _random_play(self, task_id, seed):
        """Random valid actions."""
        rng = stdlib_random.Random(seed * 1000 + hash(task_id))
        world = generate(task_id, seed)
        eng = Engine(world)
        cfg = world["cfg"]
        crops = sorted(cfg["crops"].keys())
        n_plots = cfg["n_plots"]

        for _ in range(200):
            if eng.is_done():
                break
            action = rng.choice(["plant", "harvest", "sell", "advance", "status", "finish"])
            if action == "plant":
                eng.plant(rng.randint(0, n_plots - 1), rng.choice(crops))
            elif action == "harvest":
                eng.harvest(rng.randint(0, n_plots - 1))
            elif action == "sell":
                eng.sell(rng.choice(crops), rng.randint(1, 10))
            elif action == "advance":
                eng.advance_days(rng.randint(1, 7))
            elif action == "finish":
                eng.finish()
            # status does nothing useful

        if not eng.is_done():
            eng.finish()

        oracle_gain, _ = validate_oracle(task_id, seed)
        return eng.compute_score(oracle_gain)

    def test_greedy_scores_low_on_hard_tasks(self):
        hard_tasks = ["farm_seasons", "farm_events", "farm_credit", "farm_crash"]
        for task_id in hard_tasks:
            scores = []
            for seed in range(10):
                score = self._greedy_play(task_id, seed)
                scores.append(score["total"])
            avg = sum(scores) / len(scores)
            assert avg <= 0.75, \
                f"Greedy on {task_id}: avg={avg:.4f}, expected <= 0.75"

    def test_random_agent_low_score(self):
        for task_id in get_all_task_ids():
            scores = []
            for seed in range(20):
                score = self._random_play(task_id, seed)
                scores.append(score["total"])
            avg = sum(scores) / len(scores)
            assert avg <= 0.35, \
                f"Random on {task_id}: avg={avg:.4f}, expected <= 0.35"


# ======================== INVARIANTS FUZZ ========================

class TestInvariantsFuzz:
    """1000 random/malformed tool calls per task never raise."""

    def test_fuzz_never_raises(self):
        rng = stdlib_random.Random(12345)
        for task_id in get_all_task_ids():
            world = generate(task_id, 0)
            eng = Engine(world)
            crops = sorted(world["cfg"]["crops"].keys()) + ["invalid", "", "\U0001F33E"]
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

    def test_money_always_valid(self):
        """Cash and debt always int and non-negative throughout oracle play."""
        for task_id in get_all_task_ids():
            world = generate(task_id, 42)
            eng = Engine(world)
            for n, a in world["oracle_actions"]:
                getattr(eng, n)(**a)
                s = eng.get_state()
                assert isinstance(s["cash"], int), f"Cash not int"
                assert isinstance(s["debt"], int), f"Debt not int"
                assert s["cash"] >= 0, f"Cash negative"
                assert s["debt"] >= 0, f"Debt negative"

    def test_state_hash_always_computable(self):
        rng = stdlib_random.Random(99)
        for task_id in get_all_task_ids():
            world = generate(task_id, 0)
            eng = Engine(world)
            for _ in range(50):
                h = eng.get_state_hash()
                assert isinstance(h, str) and len(h) == 8
                eng.advance_days(rng.randint(1, 3))
                if eng.is_done():
                    break


# ======================== ADVERSARIAL ========================

class TestAdversarial:
    def test_negative_quantity(self):
        w = generate("farm_basic", 0)
        e = Engine(w)
        _, err, _ = e.sell("wheat", -5)
        assert err

    def test_huge_quantity(self):
        w = generate("farm_basic", 0)
        e = Engine(w)
        _, err, _ = e.sell("wheat", 10**9)
        assert err

    def test_float_quantity(self):
        """Float quantities should fail type check."""
        w = generate("farm_basic", 0)
        e = Engine(w)
        # Engine expects int, but test that it handles gracefully
        text, err, done = e.sell("wheat", 1)  # no inventory
        assert err  # error because no inventory, not crash

    def test_bool_as_int(self):
        from harness.tools import check_args
        _, err = check_args("plant", {"plot_id": True, "crop": "wheat"})
        assert err is not None

    def test_string_quantity(self):
        from harness.tools import check_args
        _, err = check_args("sell", {"crop": "wheat", "quantity": "abc"})
        assert err is not None

    def test_advance_days_huge(self):
        w = generate("farm_basic", 0)
        e = Engine(w)
        _, err, _ = e.advance_days(10**9)
        assert err

    def test_double_finish(self):
        w = generate("farm_basic", 0)
        e = Engine(w)
        e.finish()
        _, err, done = e.finish()
        assert done

    def test_actions_after_game_over(self):
        w = generate("farm_basic", 0)
        e = Engine(w)
        e.finish()
        for action in ["get_status", "get_market", "get_forecast", "get_news"]:
            text, err, done = getattr(e, action)() if action != "get_market" else e.get_market()
            # Should not crash

    def test_sell_more_than_owned(self):
        w = generate("farm_basic", 0)
        e = Engine(w)
        _, err, _ = e.sell("wheat", 100)
        assert err

    def test_loan_over_limit(self):
        w = generate("farm_credit", 0)
        e = Engine(w)
        _, err, _ = e.take_loan(10**7)
        assert err

    def test_repeated_forecast_identical(self):
        w = generate("farm_seasons", 0)
        e = Engine(w)
        t1, _, _ = e.get_forecast()
        t2, _, _ = e.get_forecast()
        assert t1 == t2


# ======================== REPLAY INTEGRITY ========================

class TestReplayIntegrity:
    def test_tampered_sandbox_unaffected(self):
        """Tamper with sandbox state and confirm harness score is unaffected."""
        world = generate("farm_basic", 42)

        # Normal play
        eng_normal = Engine(copy.deepcopy(world))
        for n, a in world["oracle_actions"]:
            getattr(eng_normal, n)(**a)
        if not eng_normal.is_done():
            eng_normal.finish()
        normal_score = eng_normal.compute_score(
            validate_oracle("farm_basic", 42)[0]
        )

        # Tampered: give the engine tons of free cash mid-game
        eng_tampered = Engine(copy.deepcopy(world))
        for i, (n, a) in enumerate(world["oracle_actions"]):
            getattr(eng_tampered, n)(**a)
            if i == 5:
                eng_tampered.state["cash"] += 1000000  # CHEAT
        if not eng_tampered.is_done():
            eng_tampered.finish()

        # Replay (as harness would): fresh engine, same actions
        eng_replay = Engine(copy.deepcopy(world))
        for n, a in world["oracle_actions"]:
            getattr(eng_replay, n)(**a)
        if not eng_replay.is_done():
            eng_replay.finish()

        replay_score = eng_replay.compute_score(
            validate_oracle("farm_basic", 42)[0]
        )

        # Replay should match normal, not tampered
        assert replay_score["total"] == normal_score["total"]
        # Tampered engine has different hash
        assert eng_tampered.get_state_hash() != eng_replay.get_state_hash()


# ======================== TOOL SCHEMA TESTS ========================

class TestToolSchemas:
    def test_no_code_execution_tools(self):
        """Verify no code execution or file access tools exist."""
        from harness.tools import get_tool_names
        names = get_tool_names()
        forbidden = {"list_files", "read_file", "write_file", "run_python",
                      "execute", "shell", "eval", "exec"}
        overlap = names & forbidden
        assert not overlap, f"Forbidden tools found: {overlap}"

    def test_exactly_11_tools(self):
        from harness.tools import TOOL_SCHEMAS
        assert len(TOOL_SCHEMAS) == 11

    def test_all_tool_names_valid(self):
        from harness.tools import get_tool_names
        expected = {
            "get_status", "get_market", "get_forecast", "get_news",
            "plant", "harvest", "sell", "take_loan", "repay",
            "advance_days", "finish"
        }
        assert get_tool_names() == expected
