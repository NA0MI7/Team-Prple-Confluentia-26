"""
Main runner for the Seasonal Farm Market RL environment.
Orchestrates: task setup, agent interaction, telemetry, scoring.
"""
import json
import os
import sys
import time
import copy
import traceback

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.tasks import build_task, get_task_ids, get_demo_task_id
from harness.tools import TOOL_SCHEMAS, check_args, get_tool_names
from harness.env import Environment
from harness.agents import create_agent

# ======================== CONSTANTS ========================

MAX_STEPS = 40
MAX_TOOL_CALLS_PER_REPLY = 10
WALL_CLOCK_LIMIT = 600  # 10 minutes
CONTEXT_TRIM_CHARS = 40000  # ~48K tokens worth

SYSTEM_PROMPT = """You are an AI agent managing a seasonal farm market. Your goal is to maximize your net worth (cash + inventory value - debt) by the end of the game.

You interact with the farm using tool calls. Available tools:
- get_status(): Check your farm state (day, cash, plots, inventory)
- get_market(history_days): See current crop prices
- get_forecast(): Get noisy 5-day price predictions
- get_news(): Check for upcoming events
- plant(plot_id, crop): Plant a crop on a plot
- harvest(plot_id): Harvest a ready crop
- sell(crop, quantity): Sell inventory at market price
- take_loan(amount_cents): Borrow money (if available)
- repay(amount_cents): Pay back debt
- advance_days(n): Advance time by n days (1-7)
- finish(): End the game early

IMPORTANT:
- Respond ONLY with tool calls. Do not write explanations.
- Batch multiple tool calls together into a single turn (up to 10 per turn). For example, you can harvest, sell, plant new seeds, and advance days all in the same turn!
- Advance time efficiently: when crops need 2 or 3 days to grow, advance time directly (e.g. advance_days(2) or advance_days(3)). Do NOT waste turns advancing 1 day at a time unless monitoring a sensitive market event.
- Never plant crops if their grow time exceeds the remaining days before the horizon.
- Selling all inventory at once causes price slippage; sell in moderate batches over multiple days.
- Call finish() when you believe you've reached the horizon or maximized your profit.
- Each day costs taxes, so don't waste time. Plan efficiently.
"""


def run_gate_check(task_id, seed, run_id=""):
    """
    Run oracle and no-op checks for a task.
    Returns (oracle_pass, noop_pass, oracle_score, noop_score).
    Stage 3: Reference solution must score at least 0.95.
    Stage 4: Agent that gives up must score at most 0.05.
    """
    from simcore.engine import Engine

    task = build_task(task_id, seed)

    # Stage 3: Oracle check (replay oracle actions)
    oracle_eng = Engine(copy.deepcopy(task.world))
    for name, args in task.oracle_actions:
        getattr(oracle_eng, name)(**args)
    if not oracle_eng.is_done():
        oracle_eng.finish()
    oracle_score = oracle_eng.compute_score(task.oracle_gain)

    # Stage 4: No-op check (finish immediately)
    noop_eng = Engine(copy.deepcopy(task.world))
    noop_eng.finish()
    noop_score = noop_eng.compute_score(task.oracle_gain)

    oracle_pass = oracle_score["total"] >= 0.95
    noop_pass = noop_score["total"] <= 0.05

    return oracle_pass, noop_pass, oracle_score, noop_score


def run_episode(task_id, seed, model, run_id, append_text="", skip_gate=False):
    """
    Run a single episode following the strict execution flow:
      Step 3 · ORACLE: Reference solution must score at least 0.95
      Step 4 · NO-OP: Agent that gives up must score at most 0.05
      Step 5 · MODEL RUN: Starts only if both checks pass
    If either check fails: the run stops, the model is never called.
    """
    log_dir = os.path.join("logs", run_id)
    os.makedirs(log_dir, exist_ok=True)

    # Save append text
    if append_text:
        with open(os.path.join(log_dir, "append.txt"), "w") as f:
            f.write(append_text)

    # Build task
    task = build_task(task_id, seed)

    # Dynamic Pre-Run Verification: Oracle & No-Op (generated fresh for each run and seed)
    if not skip_gate:
        print("=" * 65, flush=True)
        print(f"[PRE-RUN DYNAMIC VERIFICATION] Task: {task_id} | Seed: {seed}", flush=True)
        oracle_pass, noop_pass, oracle_score, noop_score = run_gate_check(task_id, seed, run_id)

        gate_results = {
            task_id: {
                "oracle_pass": oracle_pass,
                "noop_pass": noop_pass,
                "oracle_total": oracle_score["total"],
                "noop_total": noop_score["total"],
                "PASS": oracle_pass and noop_pass,
            }
        }
        with open(os.path.join(log_dir, "gate.json"), "w") as f:
            json.dump(gate_results, f, indent=2)

        print(f"  ✓ ORACLE CHECK: Calculated Score = {oracle_score['total']:.4f} (Requirement: > 0.95) -> {'PASS' if oracle_pass else 'FAIL'} [Calculated Profit: ${oracle_score.get('gain_cents',0)/100:.2f}]", flush=True)
        if not oracle_pass:
            print(f"  [EXECUTION ABORTED] Oracle check failed ({oracle_score['total']:.4f} <= 0.95). Model will NOT be called.", flush=True)
            print("=" * 65, flush=True)
            summary = {
                "task_id": task_id,
                "seed": seed,
                "model": model,
                "termination": "gate_failed",
                "reason": f"Oracle check failed ({oracle_score['total']:.4f} <= 0.95)",
                "steps": 0,
                "score": {"total": 0.0, "oracle_score": oracle_score["total"]},
                "elapsed_seconds": 0.0,
                "run_id": run_id,
            }
            _write_outputs(log_dir, summary, [])
            return summary, []

        print(f"  ✓ NO-OP CHECK:  Calculated Score = {noop_score['total']:.4f} (Requirement: < 0.05) -> {'PASS' if noop_pass else 'FAIL'} [Calculated Profit: ${noop_score.get('gain_cents',0)/100:+.2f}]", flush=True)
        if not noop_pass:
            print(f"  [EXECUTION ABORTED] No-op check failed ({noop_score['total']:.4f} >= 0.05). Model will NOT be called.", flush=True)
            print("=" * 65, flush=True)
            summary = {
                "task_id": task_id,
                "seed": seed,
                "model": model,
                "termination": "gate_failed",
                "reason": f"No-op check failed ({noop_score['total']:.4f} >= 0.05)",
                "steps": 0,
                "score": {"total": 0.0, "oracle_score": oracle_score["total"], "noop_score": noop_score["total"]},
                "elapsed_seconds": 0.0,
                "run_id": run_id,
            }
            _write_outputs(log_dir, summary, [])
            return summary, []

        print(f"  ✓ PRE-RUN CHECKS PASSED: Oracle ({oracle_score['total']:.4f} > 0.95) & No-Op ({noop_score['total']:.4f} < 0.05). Proceeding to model execution.", flush=True)
        print("=" * 65, flush=True)

    # Step 5: Starts ONLY if both checks pass
    # Build system prompt
    full_system = SYSTEM_PROMPT + "\n\n" + task.instructions
    if append_text:
        full_system += "\n\n" + append_text

    # Create environment
    env = Environment(task)

    # Create agent
    agent = create_agent(model, task, TOOL_SCHEMAS, full_system)

    # Reset sandbox
    if not env.reset():
        # Retry once
        time.sleep(2)
        if not env.reset():
            return _crash_summary(task_id, seed, model, "sandbox_reset_failed", log_dir), []

    # Run loop
    telemetry = []
    step = 0
    start_time = time.time()
    done = False
    termination = "step_cap"

    # Initial observation
    observation = f"Game started! You are managing a farm for {task.cfg['horizon']} days.\nUse get_status() to see your current state."

    print("=" * 60, flush=True)
    print(f"[EPISODE START] Task: {task_id} (horizon={task.cfg['horizon']}d) | Seed: {seed} | Model: {model}", flush=True)
    print(f"Limits: max {MAX_STEPS} steps, {WALL_CLOCK_LIMIT}s wall-clock | Storage: {task.cfg.get('storage_cap') or 'unlimited'}", flush=True)
    if append_text:
        print(f"Appended instructions ({len(append_text)} chars): {append_text.strip()[:100]}...", flush=True)
    print("=" * 60, flush=True)

    try:
        while step < MAX_STEPS and not done:
            elapsed = time.time() - start_time
            if elapsed > WALL_CLOCK_LIMIT:
                termination = "time_cap"
                break

            step += 1

            # Capture full model input payload
            if hasattr(agent, "messages"):
                input_payload = json.dumps(agent.messages + [{"role": "user", "content": observation}], default=str)
            else:
                input_payload = str(observation)

            # Get agent response
            try:
                raw_response, tool_calls, parse_mode, token_info = agent.get_response(observation)
            except Exception as e:
                telemetry.append(_make_telemetry(
                    step, seed, task_id, input_payload, str(e), [], [],
                    [f"agent_error: {e}"], env.get_harness_state_hash(),
                    {}, token_info={}, parse_mode="error", latency_ms=0
                ))
                observation = f"Error getting response: {e}"
                print(f"[Step {step:02d}/{MAX_STEPS}] Agent error: {e}", flush=True)
                continue

            step_start = time.time()

            if not tool_calls:
                # No tool calls: log and prompt retry
                telemetry.append(_make_telemetry(
                    step, seed, task_id, input_payload,
                    json.dumps(raw_response) if raw_response else "",
                    [], [], ["no_tool_calls"], env.get_harness_state_hash(),
                    {}, token_info=token_info, parse_mode=parse_mode, latency_ms=0
                ))
                print(f"[Step {step:02d}/{MAX_STEPS}] Model returned no tool calls. Prompting retry...", flush=True)
                observation = "Please respond with tool calls. Use get_status() to check the game state, or finish() to end."
                continue

            # Process tool calls (max 10)
            all_results = []
            parsed_actions = []
            step_flags = []

            for i, tc in enumerate(tool_calls):
                if i >= MAX_TOOL_CALLS_PER_REPLY:
                    remaining = len(tool_calls) - i
                    all_results.append(f"Error: {remaining} extra tool calls exceeded the limit of {MAX_TOOL_CALLS_PER_REPLY} per reply. They were not executed.")
                    step_flags.append("excess_tool_calls")
                    break

                tc_name = tc.get("name", "")
                tc_args = tc.get("arguments", {})
                tc_id = tc.get("id", f"call_{i}")
                parsed_actions.append({
                    "tool": tc_name,
                    "args": tc_args,
                    "name": tc_name,
                    "arguments": tc_args,
                })

                # Validate tool name
                if tc_name not in get_tool_names():
                    result = f"Unknown tool '{tc_name}'. Valid tools: {', '.join(sorted(get_tool_names()))}"
                    all_results.append(f"[{tc_name}]: {result}")
                    agent.add_tool_result(tc_id, result)
                    step_flags.append("unknown_tool")
                    continue

                # Validate arguments
                cleaned_args, arg_err = check_args(tc_name, tc_args)
                if arg_err:
                    result = f"Invalid arguments for {tc_name}: {arg_err}"
                    all_results.append(f"[{tc_name}]: {result}")
                    agent.add_tool_result(tc_id, result)
                    continue

                # Execute
                try:
                    obs, is_error, tool_done = env.step(tc_name, cleaned_args)
                except Exception as e:
                    obs = f"Execution error: {e}"
                    is_error = True
                    tool_done = False
                    step_flags.append("execution_error")

                all_results.append(f"[{tc_name}]: {obs}")
                agent.add_tool_result(tc_id, obs)
                step_flags.extend(env.flags)

                if tool_done:
                    done = True
                    termination = "success" if not is_error else "failure"
                    break

            latency_ms = int((time.time() - step_start) * 1000)

            # Build observation for next step
            observation = "\n".join(all_results)

            # Compute per-step reward
            reward = env.get_step_reward()

            telemetry.append(_make_telemetry(
                step, seed, task_id, input_payload,
                json.dumps(raw_response) if raw_response else "",
                parsed_actions, all_results, step_flags,
                env.get_harness_state_hash(), reward,
                token_info=token_info, parse_mode=parse_mode,
                latency_ms=latency_ms
            ))

            # Live readable stream to terminal for judges
            print(f"[Step {step:02d}/{MAX_STEPS}] ({latency_ms}ms, parse={parse_mode})", flush=True)
            for action in parsed_actions:
                print(f"  -> Action: {action['tool']}({json.dumps(action['args'])})", flush=True)
            for res in all_results:
                first_line = res.strip().split("\n")[0]
                if len(first_line) > 120:
                    first_line = first_line[:120] + "..."
                print(f"  <- Result: {first_line}", flush=True)
            if step_flags:
                for flg in step_flags:
                    print(f"  [FLAG] {flg}", flush=True)
            print(f"  Status: net_worth=${reward.get('net_worth_cents', 0)/100:.2f} | profit={reward.get('profit', 0):.4f} | total_score={reward.get('total', 0):.4f} | state_hash={env.get_harness_state_hash()}", flush=True)

            # Trim context
            agent.trim_history(CONTEXT_TRIM_CHARS)

        # Final scoring
        if not done:
            # Force finish
            try:
                obs, is_error, _ = env.step("finish", {})
            except Exception:
                pass

        final_score = env.score()

        if termination == "step_cap" and done:
            termination = "success"

    except Exception as e:
        termination = "crash"
        final_score = env.score() if env else {"total": 0}
        step_flags = [f"crash: {traceback.format_exc()}"]

    # Build summary
    summary = {
        "task_id": task_id,
        "seed": seed,
        "model": model,
        "termination": termination,
        "steps": step,
        "score": final_score,
        "elapsed_seconds": round(time.time() - start_time, 1),
        "suspicious_count": env.suspicious_count if env else 0,
        "invalid_actions_count": env.invalid_actions_count if env else 0,
        "run_id": run_id,
    }

    print("=" * 60, flush=True)
    print(f"[EPISODE COMPLETE] Termination: {termination} | Steps: {step}/{MAX_STEPS} | Elapsed: {round(time.time() - start_time, 1)}s", flush=True)
    print(f"Final Score: {json.dumps(final_score, indent=2)}", flush=True)
    if env and env.suspicious_count > 0:
        print(f"[SECURITY AUDIT] Flagged {env.suspicious_count} suspicious behaviors | {env.invalid_actions_count} invalid action attempts.", flush=True)
    print("=" * 60, flush=True)

    # Write outputs
    _write_outputs(log_dir, summary, telemetry)

    return summary, telemetry




def _make_telemetry(step, seed, task_id, model_input, model_output_raw,
                    parsed_actions, tool_results, errors, state_hash,
                    reward, token_info=None, parse_mode="native", latency_ms=0):
    """Create a structured telemetry record strictly matching Section 07 of the spec."""
    total_tokens = 0
    if isinstance(token_info, dict):
        total_tokens = token_info.get("total_tokens", 0)
    elif isinstance(token_info, (int, float)):
        total_tokens = int(token_info)

    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "step": step,
        "seed": seed,
        "task_id": task_id,
        "model_input": model_input,
        "model_output_raw": model_output_raw,
        "parsed_actions": parsed_actions,
        "tool_result": tool_results,
        "errors": errors,
        "state": {"hash": state_hash},
        "state_hash": state_hash,
        "reward": reward,
        "reward_components": reward,
        "tokens": total_tokens,
        "token_usage": token_info or {},
        "latency_ms": latency_ms,
        "parse_mode": parse_mode,
        "flags": errors,
    }


def _crash_summary(task_id, seed, model, reason, log_dir):
    """Return a crash summary."""
    summary = {
        "task_id": task_id,
        "seed": seed,
        "model": model,
        "termination": "crash",
        "steps": 0,
        "score": {"total": 0},
        "reason": reason,
    }
    _write_outputs(log_dir, summary, [])
    return summary


def _write_outputs(log_dir, summary, telemetry):
    """Write summary.json, episode.jsonl, and telemetry.jsonl."""
    os.makedirs(log_dir, exist_ok=True)

    with open(os.path.join(log_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    if telemetry:
        # Section 07 specifies episode.jsonl
        with open(os.path.join(log_dir, "episode.jsonl"), "w") as f:
            for record in telemetry:
                f.write(json.dumps(record, default=str) + "\n")
        # Retain telemetry.jsonl for compatibility
        with open(os.path.join(log_dir, "telemetry.jsonl"), "w") as f:
            for record in telemetry:
                f.write(json.dumps(record, default=str) + "\n")
