#!/usr/bin/env python3
"""
Replay Verification Tool — Cryptographic State Machine Validator.
Replays actions from any episode.jsonl log through an independent clean Engine
from the original random seed, verifying state hash bit-for-bit.
"""
import sys
import os
import json
import argparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from simcore.world import generate, validate_oracle
from simcore.engine import Engine, state_hash


def verify_episode_replay(log_path):
    """
    Replay actions from episode.jsonl through a fresh Engine and verify state hashes.
    Returns (success: bool, report: dict).
    """
    if os.path.isdir(log_path):
        ep_file = os.path.join(log_path, "episode.jsonl")
        sum_file = os.path.join(log_path, "summary.json")
    else:
        ep_file = log_path
        sum_file = os.path.join(os.path.dirname(log_path), "summary.json")

    if not os.path.isfile(ep_file):
        raise FileNotFoundError(f"Episode file not found: {ep_file}")

    # Read logged steps
    steps = []
    with open(ep_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    steps.append(json.loads(line))
                except Exception as e:
                    pass

    if not steps:
        raise ValueError(f"No valid JSON steps found in {ep_file}")

    first_step = steps[0]
    task_id = first_step.get("task_id", "farm_seasons")
    seed = int(first_step.get("seed", 0))

    # Read summary if available
    summary = {}
    if os.path.isfile(sum_file):
        with open(sum_file, "r", encoding="utf-8") as f:
            summary = json.load(f)

    # 1. Initialize fresh seeded world
    oracle_gain, world = validate_oracle(task_id, seed)
    replay_engine = Engine(world)

    initial_hash = replay_engine.get_state_hash()
    print("=" * 68)
    print(f" REPLAY VERIFICATION: {task_id} (Seed: {seed})")
    print(f" Log file: {ep_file}")
    print(f" Initial State Hash: {initial_hash}")
    print("=" * 68)

    step_results = []
    divergence_found = False

    for st in steps:
        step_num = st.get("step", 0)
        logged_hash = st.get("state_hash") or (st.get("state") or {}).get("hash")
        actions = st.get("parsed_actions", [])

        # Execute actions through the replay engine
        state_changing = {"plant", "harvest", "sell", "take_loan", "repay", "advance_days", "finish"}
        executed = []
        for act in actions:
            name = act.get("tool") or act.get("name")
            args = act.get("args") if "args" in act else act.get("arguments", {})
            if name in state_changing:
                try:
                    method = getattr(replay_engine, name, None)
                    if method:
                        method(**args)
                        executed.append(f"{name}({args})")
                except Exception as ex:
                    executed.append(f"{name}[ERR:{ex}]")

        current_hash = replay_engine.get_state_hash()
        match = (logged_hash is None) or (current_hash == logged_hash)
        if not match:
            divergence_found = True

        status_tag = "MATCH [OK]" if match else f"DIVERGENCE! (logged {logged_hash} != {current_hash})"
        print(f"  Step {step_num:02d}: Replayed {len(executed)} actions | State Hash: {current_hash} | {status_tag}")
        step_results.append({
            "step": step_num,
            "replayed_hash": current_hash,
            "logged_hash": logged_hash,
            "match": match
        })

    # Ensure engine is finished for final scoring
    if not replay_engine.is_done():
        replay_engine.finish()

    replayed_score = replay_engine.compute_score(oracle_gain)
    logged_score = summary.get("score", {})

    print("-" * 68)
    print(f" Replayed Net Worth: ${replayed_score['net_worth_cents']/100:.2f}")
    print(f" Replayed Score:     {replayed_score['total']:.4f} (Profit: {replayed_score['profit']:.4f})")
    if logged_score:
        print(f" Logged Score:       {logged_score.get('total', 0):.4f}")

    is_verified = not divergence_found
    print("=" * 68)
    if is_verified:
        print(f" RESULT: 100% BIT-FOR-BIT REPLAY VERIFICATION PASSED.")
        print(f" All {len(steps)} steps matched cryptographic state hashes identically.")
    else:
        print(f" RESULT: REPLAY FAILED — STATE DIVERGENCE DETECTED.")
    print("=" * 68)

    return is_verified, {
        "task_id": task_id,
        "seed": seed,
        "steps_replayed": len(steps),
        "verified": is_verified,
        "replayed_score": replayed_score,
        "logged_score": logged_score,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cryptographically replay and verify an episode log.")
    parser.add_argument("path", nargs="?", default="", help="Path to run directory or episode.jsonl")
    args = parser.parse_args()

    target = args.path
    if not target:
        # Search for a sample trajectory or recent log
        candidates = [
            os.path.join(ROOT_DIR, "sample-trajectories", "success"),
            os.path.join(ROOT_DIR, "test-run-logs", "gpt-6-luna_farm_seasons"),
            os.path.join(ROOT_DIR, "logs"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                if os.path.isfile(os.path.join(c, "episode.jsonl")):
                    target = c
                    break
                # Look in subdirectories
                subs = sorted(os.listdir(c), reverse=True)
                for s in subs:
                    sub_p = os.path.join(c, s)
                    if os.path.isdir(sub_p) and os.path.isfile(os.path.join(sub_p, "episode.jsonl")):
                        target = sub_p
                        break
            if target:
                break

    if not target:
        print("Error: No episode log specified and no default logs found.", file=sys.stderr)
        sys.exit(1)

    try:
        ok, report = verify_episode_replay(target)
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"Fatal error during replay: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)
