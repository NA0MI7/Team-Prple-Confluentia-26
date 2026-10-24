"""
Main entry point for the harness container.
Handles MODE=full|all|baselines, gate checks, and episode running.
Exit codes: 0 finished, 1 crash, 2 baseline check failed, 3 bad config.
"""
import json
import os
import sys
import time
import traceback

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.runner import run_episode, run_gate_check
from harness.tasks import get_task_ids, get_demo_task_id


def main():
    # Read environment variables
    model = os.environ.get("MODEL", "mock/solver").strip() or "mock/solver"
    mode = os.environ.get("MODE", "full").strip() or "full"
    task_id = os.environ.get("TASK_ID", "").strip() or "farm_seasons"
    seed_raw = os.environ.get("SEED", "0").strip()
    seed = int(seed_raw) if seed_raw else 0
    append_file = os.environ.get("APPEND_FILE", "").strip()

    # Validate config
    if mode not in ("full", "all", "baselines"):
        print(f"ERROR: Invalid MODE '{mode}'. Must be full|all|baselines.", flush=True)
        sys.exit(3)

    # Read append text
    append_text = ""
    if append_file:
        if not os.path.isfile(append_file):
            print(f"ERROR: APPEND_FILE '{append_file}' not found.", flush=True)
            sys.exit(3)
        try:
            with open(append_file, "r") as f:
                append_text = f.read()
        except Exception as e:
            print(f"ERROR: Cannot read APPEND_FILE: {e}", flush=True)
            sys.exit(3)

    run_id = f"{model.replace('/', '_')}_{seed}_{int(time.time())}"

    if mode == "baselines":
        _run_baselines(seed, run_id)
    elif mode == "all":
        _run_all(model, seed, run_id, append_text)
    else:  # full
        _run_full(model, task_id, seed, run_id, append_text)


def _run_baselines(seed, run_id):
    """Run gate checks for all tasks. Exit 0 if all pass, 2 if any fail."""
    print("=" * 60, flush=True)
    print("MODE=baselines: Running gate checks for all tasks", flush=True)
    print("=" * 60, flush=True)

    gate_results = {}
    all_pass = True

    for tid in get_task_ids():
        oracle_pass, noop_pass, oracle_score, noop_score = run_gate_check(tid, seed, run_id)
        passed = oracle_pass and noop_pass
        oracle_profit_d = round(oracle_score.get("gain_cents", 0) / 100.0, 2)
        noop_profit_d = round(noop_score.get("gain_cents", 0) / 100.0, 2)
        gate_results[tid] = {
            "oracle_pass": oracle_pass,
            "noop_pass": noop_pass,
            "oracle_total": oracle_score["total"],
            "noop_total": noop_score["total"],
            "oracle_profit_dollars": oracle_profit_d,
            "noop_profit_dollars": noop_profit_d,
            "PASS": passed,
        }
        print(f"  ✓ [{tid}] ORACLE: {oracle_score['total']:.4f} (> 0.95 req, ${oracle_profit_d:.2f}) -> {'PASS' if oracle_pass else 'FAIL'} | NO-OP: {noop_score['total']:.4f} (< 0.05 req, ${noop_profit_d:+.2f}) -> {'PASS' if noop_pass else 'FAIL'}", flush=True)
        if not passed:
            all_pass = False

    # Save gate.json
    log_dir = os.path.join("logs", run_id)
    os.makedirs(log_dir, exist_ok=True)
    gate_path = os.path.join(log_dir, "gate.json")
    with open(gate_path, "w") as f:
        json.dump(gate_results, f, indent=2)

    print(f"\nGate results saved to {gate_path}", flush=True)

    if all_pass:
        print("\nAll gate checks PASSED.", flush=True)
        sys.exit(0)
    else:
        print("\nSome gate checks FAILED.", flush=True)
        sys.exit(2)


def _run_all(model, seed, run_id, append_text):
    """Run all tasks with the given model."""
    print("=" * 60, flush=True)
    print(f"MODE=all: Running all tasks with model={model}", flush=True)
    print("=" * 60, flush=True)

    try:
        results = {}
        for tid in get_task_ids():
            print(f"\n--- Task: {tid} ---", flush=True)

            # Gate check first
            oracle_pass, noop_pass, oracle_score, noop_score = run_gate_check(tid, seed, run_id)
            if not (oracle_pass and noop_pass):
                print(f"  Gate FAILED for {tid}, skipping.", flush=True)
                results[tid] = {"status": "gate_failed"}
                continue

            # Run episode
            task_run_id = f"{run_id}_{tid}"
            try:
                summary, _ = run_episode(tid, seed, model, task_run_id, append_text)
                results[tid] = summary
                print(f"  Score: {summary['score'].get('total', 0):.4f}, "
                      f"Termination: {summary['termination']}", flush=True)
            except Exception as e:
                print(f"  ERROR: {e}", flush=True)
                results[tid] = {"status": "error", "error": str(e)}

        # Save results
        log_dir = os.path.join("logs", run_id)
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "all_results.json"), "w") as f:
            json.dump(results, f, indent=2, default=str)

        print(f"\nResults saved to logs/{run_id}/all_results.json", flush=True)
        sys.exit(0)

    except Exception as e:
        print(f"\nCRASH in MODE=all: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)


def _run_full(model, task_id, seed, run_id, append_text):
    """Run a single task with gate checks first."""
    if not task_id:
        task_id = get_demo_task_id()
        print(f"No TASK_ID set, using demo task: {task_id}", flush=True)

    valid_tasks = get_task_ids()
    if task_id not in valid_tasks:
        print(f"ERROR: Invalid TASK_ID '{task_id}'. Valid: {valid_tasks}", flush=True)
        sys.exit(3)

    print("=" * 60, flush=True)
    print(f"MODE=full: task={task_id}, seed={seed}, model={model}", flush=True)
    print("=" * 60, flush=True)

    try:
        # Dynamic Pre-Run Verification: Oracle & No-Op
        print("=" * 65, flush=True)
        print(f"[PRE-RUN DYNAMIC VERIFICATION] Task: {task_id} | Seed: {seed}", flush=True)
        oracle_pass, noop_pass, oracle_score, noop_score = run_gate_check(task_id, seed, run_id)
        oracle_profit_d = round(oracle_score.get("gain_cents", 0) / 100.0, 2)
        noop_profit_d = round(noop_score.get("gain_cents", 0) / 100.0, 2)

        print(f"  ✓ ORACLE CHECK: Calculated Score = {oracle_score['total']:.4f} (Requirement: > 0.95) -> {'PASS' if oracle_pass else 'FAIL'} [Calculated Profit: ${oracle_profit_d:.2f}]", flush=True)
        print(f"  ✓ NO-OP CHECK:  Calculated Score = {noop_score['total']:.4f} (Requirement: < 0.05) -> {'PASS' if noop_pass else 'FAIL'} [Calculated Profit: ${noop_profit_d:+.2f}]", flush=True)

        # Save gate check results to log folder
        log_dir = os.path.join("logs", run_id)
        os.makedirs(log_dir, exist_ok=True)
        gate_results = {
            task_id: {
                "oracle_pass": oracle_pass,
                "noop_pass": noop_pass,
                "oracle_total": oracle_score["total"],
                "noop_total": noop_score["total"],
                "oracle_profit_dollars": oracle_profit_d,
                "noop_profit_dollars": noop_profit_d,
                "PASS": oracle_pass and noop_pass,
            }
        }
        with open(os.path.join(log_dir, "gate.json"), "w") as f:
            json.dump(gate_results, f, indent=2)

        if not (oracle_pass and noop_pass):
            print("\n[STOPPED] Gate check FAILED. The model was never called.", flush=True)
            sys.exit(2)

        print(f"  ✓ PRE-RUN CHECKS PASSED: Oracle ({oracle_score['total']:.4f} > 0.95) & No-Op ({noop_score['total']:.4f} < 0.05). Proceeding to model execution.", flush=True)
        print("=" * 65, flush=True)

        # Step 5: Model run
        print(f"\n[5 · MODEL RUN] Both checks passed! Starting model run with model={model}...", flush=True)
        summary, _ = run_episode(task_id, seed, model, run_id, append_text, skip_gate=True)

        print(f"\nEpisode complete:", flush=True)
        print(f"  Termination: {summary['termination']}", flush=True)
        print(f"  Steps: {summary['steps']}", flush=True)
        print(f"  Score: {json.dumps(summary['score'], indent=2)}", flush=True)
        print(f"  Elapsed: {summary.get('elapsed_seconds', 0):.1f}s", flush=True)

        exit_code = 0 if summary["termination"] != "crash" else 1
        sys.exit(exit_code)

    except SystemExit:
        raise
    except Exception as e:
        print(f"\nCRASH: {e}", flush=True)
        traceback.print_exc()
        # Write crash summary
        log_dir = os.path.join("logs", run_id)
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "summary.json"), "w") as f:
            json.dump({"termination": "crash", "error": str(e)}, f)
        sys.exit(1)


if __name__ == "__main__":
    main()
