#!/usr/bin/env python3
"""
Interactive Benchmark, Debugger & Self-Improvement Engine for Seasonal Farm Market.

Modes:
1. Single Task Debugger: Step through turns, inspect observations, tool calls, and tokens.
2. Self-Improvement Engine: Runs N randomized test cases with persistent memory and
   LLM-powered self-reflection between runs, demonstrating score improvement over time.
"""
import sys
import os
import json
import time
import copy
import random
import argparse
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer

# Ensure project root is in path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from simcore.world import generate, TASK_CONFIGS, get_all_task_ids
from simcore.engine import Engine, state_hash
from harness.tasks import build_task
from harness.tools import TOOL_SCHEMAS, check_args, get_tool_names
from harness.agents import create_agent, LLMAgent
from harness.runner import SYSTEM_PROMPT, MAX_STEPS, MAX_TOOL_CALLS_PER_REPLY
from sandbox.server import SandboxHandler
import harness.env


# 10 Available task descriptions
TASK_DESCRIPTIONS = {
    "farm_basic": {
        "title": "Basic Farming",
        "desc": "1 crop (wheat), simple plant-harvest-sell loop. Horizon: 14 days, Start Cash: $45.",
        "difficulty": "Easy"
    },
    "farm_two_crops": {
        "title": "Two Crops Diversification",
        "desc": "2 crops (wheat, tomato) with different grow times and price volatility. Horizon: 15 days.",
        "difficulty": "Easy"
    },
    "farm_seasons": {
        "title": "Seasonal Cycles & Spoilage",
        "desc": "3 crops (wheat, tomato, corn), seasonal price curves, shelf-life spoilage, 60-unit storage. Horizon: 16 days.",
        "difficulty": "Medium"
    },
    "farm_events": {
        "title": "Weather & Demand Shocks",
        "desc": "Droughts (halve harvest yield) and demand surges (+60% price). Use get_news() to anticipate. Horizon: 18 days.",
        "difficulty": "Medium"
    },
    "farm_credit": {
        "title": "Credit & Debt Management",
        "desc": "High starting debt, bank loans with daily interest, strict repayment deadline. Horizon: 18 days.",
        "difficulty": "Hard"
    },
    "farm_crash": {
        "title": "Market Crash Recovery",
        "desc": "Market price collapse midway; tests risk management and rapid recovery. Horizon: 20 days.",
        "difficulty": "Hard"
    },
    "farm_sprint": {
        "title": "Fast Turnaround Sprint",
        "desc": "Fast 10-day sprint! Rapid 2-day radishes and tomatoes. Fast execution, low token usage.",
        "difficulty": "Easy"
    },
    "farm_spoilage": {
        "title": "High Perishability Challenge",
        "desc": "Ultra-short 3-day crop shelf-lives. Strict storage limits test inventory turnover. Horizon: 15 days.",
        "difficulty": "Medium"
    },
    "farm_drought": {
        "title": "Persistent Drought Season",
        "desc": "Frequent drought periods cut yields by 50%. Tests weather anticipation and drought hedging. Horizon: 16 days.",
        "difficulty": "Hard"
    },
    "farm_market_rush": {
        "title": "High-Volatility Speculation",
        "desc": "Aggressive price swings (+/-38%) and sharp demand spikes. Tests timing and liquidity. Horizon: 16 days.",
        "difficulty": "Hard"
    },
    "econ_cobweb_cycle": {
        "title": "Cobweb Theorem (Ezekiel, 1938)",
        "desc": "Production lag boom-bust cycles. Peak spot prices crash by harvest time. Tests counter-cyclical planting. Horizon: 16 days.",
        "difficulty": "Economic Theory"
    },
    "econ_dutch_disease": {
        "title": "Dutch Disease (Corden & Neary, 1982)",
        "desc": "Hyper-lucrative Saffron inflates overhead. Day 9 price collapse punishes monoculture. Tests portfolio hedging. Horizon: 16 days.",
        "difficulty": "Economic Theory"
    },
    "econ_liquidity_mismatch": {
        "title": "Diamond-Dybvig Maturity Transformation (1983)",
        "desc": "Day 7 debt repayment deadline vs long-cycle 5-day grapes. Capital-constrained start. Tests duration matching. Horizon: 16 days.",
        "difficulty": "Economic Theory"
    },
    "econ_cournot_elasticity": {
        "title": "Cournot Oligopoly & Demand Elasticity (1838)",
        "desc": "Bountiful tomato yield (40 units) with steep 3.5% price slippage. Dumping destroys revenue; tests tranche slicing. Horizon: 15 days.",
        "difficulty": "Economic Theory"
    },
    "econ_pigouvian_commons": {
        "title": "Pigouvian Commons & Externalities (Pigou, 1920)",
        "desc": "Severe drought shock on Days 7-10 with elevated land taxes. Tests climate-resilient crop rotation. Horizon: 16 days.",
        "difficulty": "Economic Theory"
    },
    "econ_hotelling_arbitrage": {
        "title": "Hotelling Exhaustible Arbitrage (1931)",
        "desc": "Non-perishable Corn escalates on compound scarcity curve ($0.80 -> $3.50+). Tests intertemporal banking. Horizon: 16 days.",
        "difficulty": "Economic Theory"
    },
}


def load_env_file():
    """Load key-value pairs from .env if present."""
    env_path = os.path.join(ROOT_DIR, ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v


def start_local_sandbox():
    """Start an in-process sandbox HTTP server on an ephemeral port."""
    httpd = HTTPServer(("127.0.0.1", 0), SandboxHandler)
    port = httpd.server_port
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    url = f"http://127.0.0.1:{port}"
    os.environ["SANDBOX_URL"] = url
    harness.env.SANDBOX_URL = url
    return httpd, url


def distill_insights_via_llm(task_id, seed, final_score, action_summary, error_summary, current_memory, model_name):
    """
    Call the LLM API to analyze the run, diagnose errors/slippage,
    and distill reusable heuristics into persistent memory.
    """
    api_key = os.environ.get("API_KEY", "")
    base_url = os.environ.get("BASE_URL", "https://api.openai.com/v1").rstrip("/")

    # If mock model or missing key, use deterministic heuristic reflection
    if not api_key or model_name.startswith("mock/"):
        insights = []
        if final_score.get("debt_ok") == 0:
            insights.append("- Always keep at least $10-$15 cash reserve to pay daily land taxes and avoid the 15% debt penalty.")
        if final_score.get("gain_cents", 0) < final_score.get("target_cents", 1) * 0.5:
            insights.append("- Stagger crop sales: Selling all inventory at once causes severe price slippage (1.5%/unit); sell in batches of 6-8 units.")
        insights.append("- Always call get_forecast() on day 1 to identify price peaks before choosing which crop to plant.")
        return insights, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    # Prepare reflection prompt
    net_worth = final_score.get("net_worth_cents", 0) / 100
    gain = final_score.get("gain_cents", 0) / 100
    target = final_score.get("target_cents", 1) / 100
    score = final_score.get("total", 0.0)

    # Condense action summary to most recent / impactful actions to keep reasoning fast
    actions_list = [a.strip() for a in action_summary.split("\n") if a.strip()]
    condensed_actions = "\n".join(actions_list[-10:]) if len(actions_list) > 10 else action_summary

    prompt = f"""You are an AI Strategy Coach reviewing an autonomous agent's performance in a Farm Market simulation.
Scenario: {task_id} (Seed: {seed})
Score Achieved: {score:.4f} / 1.0000
Net Gain: ${gain:.2f} (Target was ${target:.2f}) | Final Net Worth: ${net_worth:.2f}
Debt Penalty: {'Yes (15% penalty applied due to unpaid debt!)' if final_score.get('debt_ok') == 0 else 'No (solvency maintained)'}

Key Recent Actions Taken:
{condensed_actions}

Errors or Bottlenecks Encountered:
{error_summary or 'None'}

Current Accumulated Memory / Skills:
{current_memory or '(None yet - this was the initial baseline run)'}

TASK:
Identify the biggest strategic error or lost profit in this run (e.g. dumping too many crops at once causing slippage, neglecting taxes, planting too close to the horizon, not checking price forecasts, crops spoiling).
Formulate 2-3 concise, actionable, and reusable SKILL RULES that the agent MUST follow in future runs to score higher.
Return ONLY bullet points starting with '-'. Do not include conversational filler."""

    body = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a concise algorithmic strategy extractor."},
            {"role": "user", "content": prompt}
        ]
    }

    # Up to 2 attempts with 90s timeout for deep reasoning models
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                f"{base_url}/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read())
                reply = data["choices"][0]["message"].get("content", "").strip()
                usage = data.get("usage") or {}
                ref_prompt = usage.get("prompt_tokens", 0) or 0
                ref_compl = usage.get("completion_tokens", 0) or 0
                ref_tokens = {
                    "prompt_tokens": ref_prompt,
                    "completion_tokens": ref_compl,
                    "total_tokens": usage.get("total_tokens", ref_prompt + ref_compl) or (ref_prompt + ref_compl)
                }
                # Extract bullet points
                lines = [l.strip() for l in reply.split("\n") if l.strip().startswith("-")]
                rules = lines if lines else [f"- {l.strip()}" for l in reply.split("\n") if l.strip()][:3]
                return rules, ref_tokens
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
                continue
            print(f"\n      ⚠️ [Reflection API Warning: {e}]", file=sys.stderr)
            # Dynamic fallback heuristic tailored to task
            horizon = TASK_CONFIGS.get(task_id, {}).get("horizon", 15)
            fallback = [
                f"- Advance time efficiently in multi-day increments (advance_days) matching crop growth cycles.",
                f"- In {task_id}: Stop planting when remaining days < grow time before horizon (Day {horizon}).",
                "- Maintain an emergency cash reserve for daily land taxes to preserve the 100% solvency multiplier."
            ]
            return ([f for f in fallback if f not in current_memory] or fallback[:2]), {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


def run_single_episode(task_id, seed, model_name, persistent_memory="", log_file=None):
    """
    Run an episode of a task.
    Optionally logs everything into log_file.
    Returns (summary_dict, action_summary, error_summary).
    """
    task = build_task(task_id, seed)
    httpd, sandbox_url = start_local_sandbox()

    full_system = SYSTEM_PROMPT + "\n\n" + task.instructions
    if persistent_memory:
        full_system += "\n\n=== LEARNED SKILLS & PERSISTENT MEMORY (FROM PREVIOUS RUNS) ===\n"
        full_system += persistent_memory
        full_system += "\n================================================================"

    env = harness.env.Environment(task)
    if not env.reset():
        return None, "", "Failed to reset sandbox"

    agent = create_agent(model_name, task, TOOL_SCHEMAS, full_system)

    step = 0
    done = False
    observation = (
        f"Game started! You are managing a farm for {task.cfg['horizon']} days.\n"
        f"Use get_status() to see your current state."
    )

    action_history = []
    error_history = []
    log_lines = []

    total_tool_calls = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0

    def log_print(msg):
        log_lines.append(msg)

    log_print(f"========================================================================")
    log_print(f"RUN LOG: Task={task_id} | Seed={seed} | Model={model_name}")
    log_print(f"Horizon: {task.cfg['horizon']} days | Plots: {task.cfg['n_plots']} | Start Cash: ${task.cfg['start_cash']/100:.2f}")
    if persistent_memory:
        log_print(f"--- ACTIVE PERSISTENT MEMORY INJECTED ---")
        log_print(persistent_memory.strip())
    else:
        log_print(f"Active Memory: None (Baseline)")
    log_print(f"========================================================================\n")

    start_time = time.time()
    max_steps = max(24, min(32, task.cfg['horizon'] + 8))
    while step < max_steps and not done:
        step += 1
        log_print(f">>> TURN {step}/{max_steps}")
        log_print(f"[INPUT OBSERVATION]:\n{observation}\n")

        try:
            raw_response, tool_calls, parse_mode, token_info = agent.get_response(observation)
        except Exception as e:
            err_msg = f"Agent API call failed: {e}"
            log_print(f"[ERROR]: {err_msg}")
            error_history.append(err_msg)
            break

        p_tok = token_info.get("prompt_tokens", 0) if token_info else 0
        c_tok = token_info.get("completion_tokens", 0) if token_info else 0
        total_prompt_tokens += p_tok
        total_completion_tokens += c_tok

        if not tool_calls:
            log_print("[NO TOOL CALLS RETURNED]")
            observation = "Please respond with tool calls. Use get_status() or finish()."
            agent.trim_history(20000)
            continue

        all_results = []
        turn_tool_calls = min(len(tool_calls), MAX_TOOL_CALLS_PER_REPLY)
        total_tool_calls += turn_tool_calls
        log_print(f"[TOOL CALLS ({len(tool_calls)})] | Turn Tokens: {p_tok + c_tok:,} (Prompt: {p_tok:,}, Completion: {c_tok:,}):")
        for i, tc in enumerate(tool_calls):
            if i >= MAX_TOOL_CALLS_PER_REPLY:
                break
            tc_name = tc.get("name", "")
            tc_args = tc.get("arguments", {})
            tc_id = tc.get("id", f"call_{i}")

            log_print(f"  ({i+1}) {tc_name}({json.dumps(tc_args)})")
            action_history.append(f"{tc_name}({json.dumps(tc_args)})")

            if tc_name not in get_tool_names():
                res = f"Unknown tool '{tc_name}'."
                all_results.append(f"[{tc_name}]: {res}")
                agent.add_tool_result(tc_id, res)
                error_history.append(res)
                continue

            cleaned_args, arg_err = check_args(tc_name, tc_args)
            if arg_err:
                res = f"Invalid arguments: {arg_err}"
                all_results.append(f"[{tc_name}]: {res}")
                agent.add_tool_result(tc_id, res)
                error_history.append(res)
                continue

            obs, is_error, tool_done = env.step(tc_name, cleaned_args)
            all_results.append(f"[{tc_name}]: {obs}")
            agent.add_tool_result(tc_id, obs)
            log_print(f"      -> {'[ERROR]' if is_error else '[RESULT]'}: {obs.split(chr(10))[0]}")
            if is_error:
                error_history.append(f"{tc_name}: {obs}")

            if tool_done:
                done = True
                break

        observation = "\n".join(all_results)
        agent.trim_history(20000)

        cur_state = env.harness_engine.get_state()
        log_print(f"  [Snapshot] Day {cur_state['day']}/{task.cfg['horizon']} | Cash: ${cur_state['cash']/100:.2f} | Debt: ${cur_state['debt']/100:.2f}\n")

    if not done:
        cur_day = env.harness_engine.get_state().get('day', 1)
        if step >= max_steps and cur_day < task.cfg['horizon']:
            budget_err = f"Step budget exhausted ({step}/{max_steps} turns) on Day {cur_day}/{task.cfg['horizon']}! Must advance time in multi-day chunks (advance_days(2-4)) and batch tool calls to complete the season."
            error_history.append(budget_err)
            log_print(f"[WARNING]: {budget_err}")
        try:
            env.step("finish", {})
        except Exception:
            pass

    final_score = env.score()
    elapsed = time.time() - start_time
    final_state = env.harness_engine.get_state()
    total_tokens = total_prompt_tokens + total_completion_tokens

    log_print(f"========================================================================")
    log_print(f"FINAL SCORECARD:")
    log_print(f"Final Cash: ${final_state['cash']/100:.2f} | Debt: ${final_state['debt']/100:.2f}")
    log_print(f"Net Gain: ${final_score['gain_cents']/100:.2f} (Target: ${final_score['target_cents']/100:.2f})")
    log_print(f"Profit Ratio: {final_score['profit']:.4f} | Solvency: {'1.00' if final_score['debt_ok'] else '0.85'}")
    log_print(f"Total Benchmark Score: {final_score['total']:.4f} ({final_score['total']*100:.1f}%)")
    log_print(f"Turns: {step}/{max_steps} | Tool Calls: {total_tool_calls}")
    log_print(f"Tokens Exhausted: {total_tokens:,} (Prompt: {total_prompt_tokens:,} | Completion: {total_completion_tokens:,})")
    log_print(f"Elapsed Time: {elapsed:.1f}s")
    log_print(f"========================================================================")

    # Save to file if path provided
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))

    # Compact summaries for reflection prompt
    act_summary = "\n".join([f"- {a}" for a in action_history[:15]])
    err_summary = "\n".join([f"- {e}" for e in list(set(error_history))[:5]])

    metrics = {
        "turns": step,
        "max_steps": max_steps,
        "tool_calls": total_tool_calls,
        "prompt_tokens": total_prompt_tokens,
        "completion_tokens": total_completion_tokens,
        "total_tokens": total_tokens,
        "elapsed": elapsed
    }

    return final_score, act_summary, err_summary, metrics


def run_self_improvement_benchmark(num_runs, model_name, suite="econ", fixed_task=None):
    """
    Demonstrate self-improving properties of the LLM:
    - If fixed_task is specified: runs N iterations of that exact economic theory across random seeds.
    - Otherwise runs N randomized test cases from the selected suite.
    - At start of session, memory is refreshed (empty).
    - Across runs, memory persists and accumulates insights via LLM reflection.
    - CLI outputs clean score improvements and distilled rules.
    - Full turn-by-turn logs saved in separate txt files.
    """
    if fixed_task:
        task_pool = [fixed_task]
        theory_title = TASK_DESCRIPTIONS.get(fixed_task, {}).get("title", fixed_task)
        suite_title = f"Focused Single Theory Repeated: {fixed_task} ({theory_title})"
    elif suite == "econ":
        task_pool = [k for k in get_all_task_ids() if k.startswith("econ_")]
        suite_title = "Economic Theory Benchmarks (Advanced Strategic Dynamics)"
    elif suite == "standard":
        task_pool = [k for k in get_all_task_ids() if not k.startswith("econ_")]
        suite_title = "Standard Farming Tasks (Operational Mechanics)"
    else:
        task_pool = get_all_task_ids()
        suite_title = "All 16 Combined Benchmarks"

    print("\n" + "=" * 76)
    print("      SELF-IMPROVING BENCHMARK MODE (PERSISTENT MEMORY)")
    print(f"      Target: {suite_title}")
    print(f"      Total Test Cases: {num_runs} | Model: {model_name}")
    print("=" * 76)
    print("• Session Memory is fresh (cleared).")
    if fixed_task:
        print(f"• Every run tests the SAME theory ({fixed_task}) with a different random seed.")
    else:
        print("• Each run tests a randomized scenario from the suite and random seed.")
    print("• After each run, the LLM reflects and appends new skills to memory.")
    print("• Full transcripts logged to: logs/self_improvement/")
    print("=" * 76)

    session_id = f"session_{int(time.time())}"
    log_dir = os.path.join(ROOT_DIR, "logs", "self_improvement", session_id)
    os.makedirs(log_dir, exist_ok=True)

    persistent_memory = ""
    memory_history = []
    run_records = []

    for i in range(1, num_runs + 1):
        # Pick randomized task and seed
        task_id = random.choice(task_pool)
        seed = random.randint(0, 9999)
        horizon = TASK_CONFIGS[task_id]["horizon"]

        print(f"\n[{i}/{num_runs}] EXECUTING: {task_id:<17} (Seed: {seed:<5} | Horizon: {horizon}d)")
        if not persistent_memory:
            print("      🧠 Memory Status: [Empty - Baseline Run]")
        else:
            num_rules = len([l for l in persistent_memory.split("\n") if l.strip().startswith("-")])
            print(f"      🧠 Memory Status: [Active - Injected {num_rules} Learned Rules]")

        log_path = os.path.join(log_dir, f"run_{i}_{task_id}_seed{seed}.txt")

        # Run the episode
        score, act_sum, err_sum, metrics = run_single_episode(
            task_id, seed, model_name, persistent_memory, log_file=log_path
        )

        gain_str = f"${score['gain_cents']/100:.2f}"
        target_str = f"${score['target_cents']/100:.2f}"
        pct = (score['gain_cents'] / score['target_cents'] * 100) if score['target_cents'] > 0 else 0
        total_score = score["total"]

        print(f"      📊 Score:      {total_score:.4f} ({pct:+.1f}% of Target | Gain: {gain_str} / Target: {target_str})")
        print(f"      🔄 Turns:      {metrics['turns']}/{metrics['max_steps']} turns taken")
        print(f"      🛠️  Tool Calls: {metrics['tool_calls']} calls executed")
        print(f"      🪙 Tokens:     {metrics['total_tokens']:,} exhausted ({metrics['prompt_tokens']:,} prompt + {metrics['completion_tokens']:,} completion)")
        print(f"      ⏱️  Time:       {metrics['elapsed']:.1f}s")
        print(f"      📁 Detailed Log: logs/self_improvement/{session_id}/run_{i}_{task_id}_seed{seed}.txt")

        # Distill new insights via LLM reflection
        print(f"      ⚡ Distilling insights via LLM reflection...")
        new_insights, ref_tokens = distill_insights_via_llm(
            task_id, seed, score, act_sum, err_sum, persistent_memory, model_name
        )

        # Update persistent memory
        newly_added = 0
        for r in new_insights:
            if r not in persistent_memory:
                persistent_memory += f"{r}\n"
                newly_added += 1

        total_rules = len([l for l in persistent_memory.split("\n") if l.strip().startswith("-")])
        ref_tokens_str = f" [Reflection: {ref_tokens['total_tokens']:,} tokens]" if ref_tokens['total_tokens'] > 0 else ""
        print(f"      💡 Learned Skills Distilled ({newly_added} new rules added | {total_rules} total in memory){ref_tokens_str}:")
        for rule in new_insights:
            print(f"         {rule}")

        run_total_tokens = metrics["total_tokens"] + ref_tokens["total_tokens"]

        run_records.append({
            "run": i,
            "task": task_id,
            "seed": seed,
            "score": total_score,
            "gain": score["gain_cents"],
            "target": score["target_cents"],
            "turns": metrics["turns"],
            "max_steps": metrics["max_steps"],
            "tool_calls": metrics["tool_calls"],
            "prompt_tokens": metrics["prompt_tokens"],
            "completion_tokens": metrics["completion_tokens"],
            "game_tokens": metrics["total_tokens"],
            "ref_tokens": ref_tokens["total_tokens"],
            "run_total_tokens": run_total_tokens,
            "elapsed": metrics["elapsed"],
            "new_insights_count": newly_added
        })

    # Final Improvement Scorecard
    print("\n" + "=" * 96)
    print("                              SELF-IMPROVEMENT SCORECARD")
    print("=" * 96)
    print(f"{'Run':<4} | {'Task':<17} | {'Score':<8} | {'Progression':<13} | {'Turns':<7} | {'Tool Calls':<10} | {'Tokens':<11} | {'Time':<6}")
    print("-" * 96)
    baseline_score = run_records[0]["score"] if run_records else 0.0
    for idx, r in enumerate(run_records):
        delta = r["score"] - baseline_score
        delta_str = f"{delta:+.4f}" if idx > 0 else "Baseline"
        arrow = "▲" if delta > 0 and idx > 0 else ("▼" if delta < 0 else "—")
        prog_str = f"{delta_str} {arrow}"
        turns_str = f"{r['turns']}/{r['max_steps']}"
        print(f" #{r['run']:<2} | {r['task']:<17} | {r['score']:<8.4f} | {prog_str:<13} | {turns_str:<7} | {r['tool_calls']:<10} | {r['run_total_tokens']:<11,} | {r['elapsed']:<5.1f}s")
    print("=" * 96)

    avg_score = sum(r["score"] for r in run_records) / len(run_records) if run_records else 0
    final_rule_count = len([l for l in persistent_memory.split("\n") if l.strip().startswith("-")])
    total_turns_all = sum(r["turns"] for r in run_records)
    total_tools_all = sum(r["tool_calls"] for r in run_records)
    total_tokens_all = sum(r["run_total_tokens"] for r in run_records)

    print(f"• Baseline Score (Run #1):    {baseline_score:.4f}")
    print(f"• Average Score Across Runs:  {avg_score:.4f}")
    print(f"• Total Simulation Turns:     {total_turns_all} turns")
    print(f"• Total Tool Calls Made:      {total_tools_all} tool calls")
    print(f"• Total Tokens Exhausted:     {total_tokens_all:,} tokens (gameplay + reflection)")
    print(f"• Total Rules in Memory:      {final_rule_count} persistent heuristics accumulated")
    print(f"• All Run Transcripts Saved:  logs/self_improvement/{session_id}/")
    print("=" * 96)


def select_task_interactively():
    """Display available tasks grouped into Economic Theory Benchmarks and Standard Tasks."""
    print("\nSelect a Benchmark Task (16 Scenarios Available):")
    print("=" * 76)
    print("  📈 ECONOMIC THEORY BENCHMARKS (Latent Dynamics, Fallacies & Deep Learning):")
    print("  " + "-" * 74)
    econ_keys = [k for k in TASK_DESCRIPTIONS.keys() if k.startswith("econ_")]
    for idx, key in enumerate(econ_keys, 1):
        info = TASK_DESCRIPTIONS[key]
        print(f"  [{idx:2d}] {key:<25} | {info['title']}")
        print(f"       {info['desc']}")

    print("\n  🚜 STANDARD FARMING TASKS (Operational & Horizon Challenges):")
    print("  " + "-" * 74)
    std_keys = [k for k in TASK_DESCRIPTIONS.keys() if not k.startswith("econ_")]
    all_keys = econ_keys + std_keys
    for idx, key in enumerate(std_keys, len(econ_keys) + 1):
        info = TASK_DESCRIPTIONS[key]
        print(f"  [{idx:2d}] {key:<25} | {info['title']} ({info['difficulty']})")
        print(f"       {info['desc']}")
    print("=" * 76)

    while True:
        choice = input(f"Choose a task [1-{len(all_keys)}] (default: 1 - econ_cobweb_cycle): ").strip()
        if not choice:
            return "econ_cobweb_cycle"
        if choice.isdigit() and 1 <= int(choice) <= len(all_keys):
            return all_keys[int(choice) - 1]
        if choice in TASK_DESCRIPTIONS:
            return choice
        print("Invalid choice, please enter a number or task name.")


def main():
    load_env_file()
    parser = argparse.ArgumentParser(description="Seasonal Farm Market Debugger & Self-Improvement Engine")
    parser.add_argument("--task", type=str, default=None, help="Task ID for single task run")
    parser.add_argument("--seed", type=int, default=None, help="Random seed (default: 0)")
    parser.add_argument("--model", type=str, default=None, help="Model name (e.g., gpt-6-luna, mock/solver)")
    parser.add_argument("--auto", action="store_true", help="Auto-run without pausing between turns")
    parser.add_argument("--self-improve", action="store_true", help="Launch self-improvement loop across multiple test cases")
    parser.add_argument("--runs", type=int, default=3, help="Number of test cases for self-improvement mode (default: 3)")
    parser.add_argument("--suite", type=str, choices=["econ", "standard", "all"], default="econ", help="Benchmark suite (default: econ)")
    args = parser.parse_args()

    print("=" * 72)
    print("      SEASONAL FARM MARKET — AGENT & BENCHMARK SUITE")
    print("=" * 72)

    # Determine model
    if args.model:
        model_name = args.model
    else:
        default_model = os.environ.get("MODEL", "gpt-6-luna")
        model_name = default_model

    # Check if user invoked self-improvement mode via flag
    if args.self_improve:
        run_self_improvement_benchmark(args.runs, model_name, suite=args.suite, fixed_task=args.task)
        return

    # Check interactive mode menu
    if not args.task:
        print("\nChoose Operation Mode:")
        print("  [1] Self-Improvement Engine (Run N test cases with persistent memory & reflection)")
        print("  [2] Single Task Deep Debugger (Inspect turn-by-turn messages, tools, & tokens)")
        mode_choice = input("\nSelect Mode [1 or 2] (default: 1): ").strip()

        if mode_choice in ("1", ""):
            runs_input = input(f"Enter number of test cases to run (default: 3): ").strip()
            num_runs = int(runs_input) if runs_input.isdigit() else 3

            print("\nSelect Benchmark Mode for Self-Improvement:")
            print("  [1] Economic Theory Suite (Randomized across Cobweb, Dutch Disease, Liquidity, Cournot, etc.)")
            print("  [2] Focus on ONE Specific Theory Repeatedly (Run N iterations of same theory across new seeds) [Recommended]")
            print("  [3] Standard Farming Tasks (Basic, Seasons, Drought, Crash, etc.)")
            print("  [4] All 16 Combined Benchmarks")
            suite_choice = input("Select Option [1, 2, 3, or 4] (default: 2): ").strip()
            if suite_choice in ("2", ""):
                print("\nChoose the theory to test repeatedly across runs:")
                chosen_theory = select_task_interactively()
                run_self_improvement_benchmark(num_runs, model_name, fixed_task=chosen_theory)
                return
            elif suite_choice == "3":
                suite = "standard"
            elif suite_choice == "4":
                suite = "all"
            else:
                suite = "econ"

            run_self_improvement_benchmark(num_runs, model_name, suite=suite)
            return

        # Otherwise continue to single task debugger
        task_id = select_task_interactively()
    else:
        task_id = args.task

    # Determine seed
    if args.seed is not None:
        seed = args.seed
    else:
        seed_env = os.environ.get("SEED", "0")
        seed_input = input(f"\nEnter Random Seed (default: {seed_env}): ").strip()
        seed = int(seed_input) if seed_input.isdigit() else int(seed_env)

    # Single task execution
    print(f"\nRunning Single Task Debugger: Task={task_id}, Seed={seed}, Model={model_name}")
    score, _, _, metrics = run_single_episode(task_id, seed, model_name)
    print("\n" + "=" * 55)
    print("SINGLE TASK EXECUTION METRICS:")
    print(f"• Final Score:      {score['total']:.4f} ({score['total']*100:.1f}%)")
    print(f"• Net Gain:         ${score['gain_cents']/100:.2f} (Target: ${score['target_cents']/100:.2f})")
    print(f"• Turns Taken:      {metrics['turns']} / {metrics['max_steps']}")
    print(f"• Tool Calls Made:  {metrics['tool_calls']}")
    print(f"• Tokens Exhausted: {metrics['total_tokens']:,} (Prompt: {metrics['prompt_tokens']:,} | Completion: {metrics['completion_tokens']:,})")
    print(f"• Wall-Clock Time:  {metrics['elapsed']:.1f}s")
    print("=" * 55)


if __name__ == "__main__":
    main()
