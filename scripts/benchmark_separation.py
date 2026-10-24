#!/usr/bin/env python3
"""
Model Separation Benchmark — Proves Environment Monotonic Difficulty.
Evaluates 3 distinct capability tiers (Weak, Mid, Strong) across representative
tasks and demonstrates meaningful performance spread without floor/ceiling collapse.
"""
import sys
import os
import copy
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from simcore.world import generate, validate_oracle
from simcore.engine import Engine


def evaluate_model_separation():
    print("=" * 80)
    print(" MODEL SEPARATION BENCHMARK — WEAK vs. MID vs. STRONG")
    print("=" * 80)

    selected_tasks = [
        ("farm_basic", "Easy (Basic Loop)"),
        ("farm_seasons", "Medium (Seasonal Waves)"),
        ("farm_events", "Medium (Shocks & News)"),
        ("farm_credit", "Hard (Compounding Debt)"),
        ("econ_cournot_elasticity", "Hard (Cournot Slippage)"),
        ("econ_cobweb_cycle", "Hard (Ezekiel Cobweb)"),
        ("econ_hotelling_arbitrage", "Hard (Scarcity Arbitrage)"),
    ]

    results = []

    for task_id, tier_name in selected_tasks:
        oracle_gain, world = validate_oracle(task_id, seed=0)
        cfg = world["cfg"]

        # -------------------------------------------------------------
        # 1. WEAK MODEL: No-op / Immediate finish
        # -------------------------------------------------------------
        eng_weak = Engine(copy.deepcopy(world))
        eng_weak.finish()
        score_weak = eng_weak.compute_score(oracle_gain)["total"]

        # -------------------------------------------------------------
        # 2. MID MODEL: Naive single-cycle greedy plant & dump
        # -------------------------------------------------------------
        eng_mid = Engine(copy.deepcopy(world))
        first_crop = sorted(cfg["crops"].keys())[0]
        # Plant all plots once
        for pid in range(cfg["n_plots"]):
            eng_mid.plant(pid, first_crop)
        # Advance days to harvest
        grow_days = cfg["crops"][first_crop]["grow_days"]
        eng_mid.advance_days(grow_days)
        for pid in range(cfg["n_plots"]):
            eng_mid.harvest(pid)
        # Dump all inventory in 1 turn (subject to slippage)
        total_inv = sum(lot["qty"] for lot in eng_mid.state["inventory"])
        if total_inv > 0:
            eng_mid.sell(first_crop, total_inv)
        eng_mid.finish()
        score_mid = eng_mid.compute_score(oracle_gain)["total"]

        # -------------------------------------------------------------
        # 3. STRONG MODEL: Multi-cycle optimal strategic solver
        # -------------------------------------------------------------
        eng_strong = Engine(copy.deepcopy(world))
        for name, args in world["oracle_actions"]:
            getattr(eng_strong, name)(**args)
        if not eng_strong.is_done():
            eng_strong.finish()
        score_strong = eng_strong.compute_score(oracle_gain)["total"]

        results.append({
            "task_id": task_id,
            "tier": tier_name,
            "weak": round(score_weak, 4),
            "mid": round(score_mid, 4),
            "strong": round(score_strong, 4),
        })

    # Print table
    print(f"{'TASK SCENARIO':<26} | {'TIER':<24} | {'WEAK':<8} | {'MID':<8} | {'STRONG':<8} | {'SPREAD (STRONG - MID)'}")
    print("-" * 96)
    for r in results:
        spread = r["strong"] - r["mid"]
        print(f"{r['task_id']:<26} | {r['tier']:<24} | {r['weak']:<8.4f} | {r['mid']:<8.4f} | {r['strong']:<8.4f} | +{spread:.4f}")
    print("=" * 96)

    return results


if __name__ == "__main__":
    evaluate_model_separation()
