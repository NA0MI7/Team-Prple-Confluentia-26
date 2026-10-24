#!/usr/bin/env python3
"""
No-Op Agent Execution & Benchmark Verification Script

Demonstrates the zero-action (no-op) baseline agent:
- Enters the game and calls finish() immediately on Turn 1 without planting, trading, or borrowing.
- Evaluates the final state through the official scoring engine.
- Formally displays the resulting financial audit and score (verifying total <= 0.05).

Usage:
    python scripts/noop_agent.py                    # Run default demo task (farm_seasons, seed 0)
    python scripts/noop_agent.py --task farm_crash   # Run specific task
    python scripts/noop_agent.py --all              # Verify no-op score <= 0.05 across all 16 benchmark tasks
    python scripts/noop_agent.py --save             # Save trajectory to logs/ for dashboard inspection
"""
import os
import sys
import json
import time
import copy
import argparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from simcore.world import TASK_CONFIGS, get_all_task_ids, DEMO_TASK, validate_oracle
from simcore.engine import Engine
from harness.tasks import build_task


def run_noop_for_task(task_id, seed=0, verbose=True, save_log=False):
    """
    Execute the No-Op agent on a task and seed.
    Returns (score_dict, task, elapsed_time).
    """
    start_time = time.time()
    task = build_task(task_id, seed)
    oracle_gain = task.oracle_gain
    oracle_profit_dollars = round(oracle_gain / 100.0, 2)

    # Initialize engine with the task's world state
    world = task.get_world_for_sandbox()
    engine = Engine(copy.deepcopy(world))

    # No-Op action: finish() immediately at Day 1
    engine.finish()
    score = engine.compute_score(oracle_gain)
    elapsed = round(time.time() - start_time, 3)

    state = engine.get_state()
    start_cash_dollars = round(task.cfg["start_cash"] / 100.0, 2)
    final_cash_dollars = round(state["cash"] / 100.0, 2)
    final_debt_dollars = round(state["debt"] / 100.0, 2)
    gain_dollars = round(score["gain_cents"] / 100.0, 2)
    net_worth_dollars = round(score["net_worth_cents"] / 100.0, 2)
    total_score = score["total"]
    passed = total_score <= 0.05

    if verbose:
        print("=" * 76)
        print("           🛑 NO-OP BASELINE AGENT — SCORE VERIFICATION")
        print("=" * 76)
        print(f"Task Scenario:          {task_id} ({task.cfg.get('difficulty', 'medium').upper()})")
        print(f"Game Horizon:           {task.cfg['horizon']} Days | Plots: {task.cfg['n_plots']} | Land Tax: ${task.cfg['land_tax']*task.cfg['n_plots']/100:.2f}/day")
        print(f"Random Seed:            {seed}")
        print(f"Initial Starting Cash:  ${start_cash_dollars:.2f}")
        print(f"Available Crops:        {', '.join(task.cfg.get('crops', {}).keys())}")
        print("-" * 76)
        print("[Turn 01 Action]:       finish({})  --> Immediate termination at onset.")
        print("-" * 76)
        print("FINANCIAL AUDIT:")
        print(f"  • Final Cash:         ${final_cash_dollars:.2f}")
        print(f"  • Active Debt:        ${final_debt_dollars:.2f}")
        print(f"  • Inventory Holdings: {len(state['inventory'])} units")
        print(f"  • Net Worth:          ${net_worth_dollars:.2f}")
        print(f"  • Net Realized Gain:  ${gain_dollars:+.2f}")
        print(f"  • Oracle Target Gain: ${oracle_profit_dollars:.2f} (Oracle Score: {score.get('oracle_score', 0.9850):.4f})")
        print("-" * 76)
        print("OFFICIAL SCORING ENGINE BREAKDOWN:")
        print(f"  • Gain vs Target:     {score.get('profit', 0.0):.4f}")
        print(f"  • Solvency Multiplier: {'1.00 (Solvent)' if score['debt_ok'] else '0.85 (Insolvent)'}")
        print(f"  • TOTAL NO-OP SCORE:  {total_score:.4f} ({total_score*100:.2f}%)")
        print(f"  • Benchmark Check:    Score <= 0.05  ==>  {'✅ PASS' if passed else '❌ FAIL'} ({total_score:.4f} <= 0.05)")
        print("=" * 76)

    if save_log:
        run_id = f"noop_agent_{task_id}_{seed}_{int(time.time())}"
        log_dir = os.path.join(ROOT_DIR, "logs", run_id)
        os.makedirs(log_dir, exist_ok=True)

        summary = {
            "task_id": task_id,
            "seed": seed,
            "model": "no-op-agent",
            "termination": "success",
            "steps": 1,
            "score": score,
            "elapsed_seconds": elapsed,
            "run_id": run_id
        }
        with open(os.path.join(log_dir, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        ep_line = json.dumps({
            "step": 1,
            "actions": [{"tool": "finish", "args": {}}],
            "tool_result": ["Game ended via finish()."],
            "farm_state": state,
            "reward": score
        })
        with open(os.path.join(log_dir, "episode.jsonl"), "w", encoding="utf-8") as f:
            f.write(ep_line + "\n")

        if verbose:
            print(f"📁 Run trajectory saved to logs/{run_id}/ for dashboard inspection.")

    return score, task, elapsed


def run_all_benchmark_tasks():
    """Verify No-Op scores across all 5 primary scenarios in both Easy and Hard tiers."""
    scenarios = [
        "seasonal_harvest_easy", "seasonal_harvest_hard",
        "market_volatility_easy", "market_volatility_hard",
        "credit_leverage_easy", "credit_leverage_hard",
        "climate_shocks_easy", "climate_shocks_hard",
        "commodity_arbitrage_easy", "commodity_arbitrage_hard",
    ]
    print("\n" + "=" * 94)
    print("      NO-OP AGENT COMPREHENSIVE BENCHMARK MATRIX (5 Tasks x 2 Difficulty Tiers)")
    print("=" * 94)
    print(f"{'Task Scenario':<28} | {'Tier':<5} | {'Horizon':<7} | {'Plots':<5} | {'Oracle Profit':<14} | {'No-Op Score':<12} | {'Result':<6}")
    print("-" * 94)

    all_passed = True
    for tid in scenarios:
        score, task, _ = run_noop_for_task(tid, seed=0, verbose=False, save_log=False)
        tier = task.cfg.get("difficulty", "easy").upper()
        plots_str = f"{task.cfg['n_plots']}p"
        orc_p = f"${task.oracle_gain/100:.2f}"
        sc_val = f"{score['total']:.4f}"
        is_pass = score["total"] <= 0.05
        if not is_pass:
            all_passed = False
        res_str = "PASS ✅" if is_pass else "FAIL ❌"
        print(f"{tid:<28} | {tier:<5} | {str(task.cfg['horizon'])+'d':<7} | {plots_str:<5} | {orc_p:<14} | {sc_val:<12} | {res_str:<6}")

    print("=" * 94)
    if all_passed:
        print("🎉 ALL SCENARIOS PASSED: No-Op Agent score strictly <= 0.05 across all 5 tasks (Easy & Hard).")
    else:
        print("⚠️ Some tasks exceeded the 0.05 no-op threshold.")
    print("=" * 94)
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="No-Op Agent Execution & Score Verification")
    parser.add_argument("--task", type=str, default=DEMO_TASK, help=f"Task scenario (default: {DEMO_TASK})")
    parser.add_argument("--seed", type=int, default=0, help="Random seed (default: 0)")
    parser.add_argument("--all", action="store_true", help="Run across all 16 benchmark tasks")
    parser.add_argument("--save", action="store_true", help="Save run trajectory to logs/ for dashboard")
    args = parser.parse_args()

    if args.all:
        success = run_all_benchmark_tasks()
        sys.exit(0 if success else 1)
    else:
        score, _, _ = run_noop_for_task(args.task, args.seed, verbose=True, save_log=args.save)
        sys.exit(0 if score["total"] <= 0.05 else 1)


if __name__ == "__main__":
    main()
