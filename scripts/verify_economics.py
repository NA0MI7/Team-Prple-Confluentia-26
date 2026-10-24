#!/usr/bin/env python3
"""
Empirical Economic Verifier — Measures Naive vs. Strategic Policies.
Runs real engine simulations for all 6 advanced economic trap tasks,
measuring exact Net Worth, Realized Revenue, and Scores.
"""
import sys
import os
import copy
import json

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from simcore.world import generate, validate_oracle
from simcore.engine import Engine


def evaluate_naive_vs_smart():
    print("=" * 80)
    print(" EMPIRICAL ECONOMIC BENCHMARKS: NAIVE TRAP VS. OPTIMAL STRATEGY")
    print("=" * 80)

    benchmarks = [
        "econ_cournot_elasticity",
        "econ_cobweb_cycle",
        "econ_liquidity_mismatch",
        "econ_hotelling_arbitrage",
        "econ_dutch_disease",
        "econ_pigouvian_commons",
    ]

    results = []

    for task_id in benchmarks:
        oracle_gain, world = validate_oracle(task_id, seed=0)
        cfg = world["cfg"]
        start_cash = cfg["start_cash"]

        # ---------------------------------------------------------
        # 1. OPTIMAL (ORACLE) RUN
        # ---------------------------------------------------------
        eng_smart = Engine(copy.deepcopy(world))
        for name, args in world["oracle_actions"]:
            getattr(eng_smart, name)(**args)
        if not eng_smart.is_done():
            eng_smart.finish()
        score_smart = eng_smart.compute_score(oracle_gain)

        # ---------------------------------------------------------
        # 2. NAIVE TRAP RUNS (Empirical heuristic for each phenomenon)
        # ---------------------------------------------------------
        eng_naive = Engine(copy.deepcopy(world))

        if task_id == "econ_cournot_elasticity":
            # Naive: Plants all plots, harvests all, and dumps entire inventory in a SINGLE batch (massive slippage)
            for pid in range(cfg["n_plots"]):
                eng_naive.plant(pid, "tomato")
            eng_naive.advance_days(3)
            for pid in range(cfg["n_plots"]):
                eng_naive.harvest(pid)
            # Dump all 28 units at once
            eng_naive.sell("tomato", 28)
            for pid in range(cfg["n_plots"]):
                eng_naive.plant(pid, "tomato")
            eng_naive.advance_days(3)
            for pid in range(cfg["n_plots"]):
                eng_naive.harvest(pid)
            eng_naive.sell("tomato", 28)
            eng_naive.finish()

        elif task_id == "econ_cobweb_cycle":
            # Naive: Sees high initial Strawberry price on day 1 ($2.80), plants all Strawberry on day 1.
            # Harvests on day 5 right into the peak supply glut when price crashes by 58%!
            for pid in range(cfg["n_plots"]):
                eng_naive.plant(pid, "strawberry")
            eng_naive.advance_days(4)
            for pid in range(cfg["n_plots"]):
                eng_naive.harvest(pid)
            # Panics and sells at the bottom
            eng_naive.sell("strawberry", 24)
            eng_naive.finish()

        elif task_id == "econ_liquidity_mismatch":
            # Naive: Borrows maximum loan ($60.00), commits all capital into 5-day slow crop (grape),
            # exhausts cash buffer, and fails to repay debt by deadline day 7.
            eng_naive.take_loan(cfg["credit_limit"])
            for pid in range(cfg["n_plots"]):
                eng_naive.plant(pid, "grape")
            # Advance past repayment deadline without cash
            eng_naive.advance_days(7)
            eng_naive.finish()

        elif task_id == "econ_hotelling_arbitrage":
            # Naive: Sells durable corn immediately on day 4 harvest at $1.20, forfeiting end-of-season scarcity
            for pid in range(cfg["n_plots"]):
                eng_naive.plant(pid, "corn")
            eng_naive.advance_days(4)
            for pid in range(cfg["n_plots"]):
                eng_naive.harvest(pid)
            eng_naive.sell("corn", 28)
            eng_naive.finish()

        elif task_id == "econ_dutch_disease":
            # Naive: Booming sector trap: All-in on Saffron even on day 7, holding inventory through the structural -65% crash
            for pid in range(cfg["n_plots"]):
                eng_naive.plant(pid, "saffron")
            eng_naive.advance_days(6)
            for pid in range(cfg["n_plots"]):
                eng_naive.harvest(pid)
            # Plants Saffron again right before crash
            for pid in range(cfg["n_plots"]):
                eng_naive.plant(pid, "saffron")
            eng_naive.advance_days(6)
            for pid in range(cfg["n_plots"]):
                eng_naive.harvest(pid)
            # Sells post-crash
            eng_naive.sell("saffron", 32)
            eng_naive.finish()

        elif task_id == "econ_pigouvian_commons":
            # Naive: Overplants intensive crop without rotation, causing yield degradation
            for pid in range(cfg["n_plots"]):
                eng_naive.plant(pid, "sugarcane")
            eng_naive.advance_days(4)
            for pid in range(cfg["n_plots"]):
                eng_naive.harvest(pid)
            eng_naive.sell("sugarcane", 20)
            eng_naive.finish()

        score_naive = eng_naive.compute_score(oracle_gain)

        diff = score_smart["total"] - score_naive["total"]
        results.append({
            "task_id": task_id,
            "phenomenon": cfg.get("economic_concept", task_id.replace("econ_", "").replace("_", " ").title()),
            "start_cash": f"${start_cash/100:.2f}",
            "naive_worth": f"${score_naive['net_worth_cents']/100:.2f}",
            "smart_worth": f"${score_smart['net_worth_cents']/100:.2f}",
            "naive_score": round(score_naive["total"], 4),
            "smart_score": round(score_smart["total"], 4),
            "separation": round(diff, 4)
        })

    # Print empirical table
    print(f"{'TASK ID':<26} | {'NAIVE NET WORTH':<15} | {'SMART NET WORTH':<15} | {'NAIVE SCORE':<11} | {'SMART SCORE':<11} | {'SEPARATION'}")
    print("-" * 105)
    for r in results:
        print(f"{r['task_id']:<26} | {r['naive_worth']:<15} | {r['smart_worth']:<15} | {r['naive_score']:<11.4f} | {r['smart_score']:<11.4f} | +{r['separation']:.4f}")
    print("=" * 105)

    return results


if __name__ == "__main__":
    evaluate_naive_vs_smart()
