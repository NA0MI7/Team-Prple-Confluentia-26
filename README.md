# Seasonal Farm Market — Unbreakable RL Environment for AI Agents

A high-integrity Reinforcement Learning (RL) simulation environment where an LLM agent manages a small farm economy across multi-day horizons through structured tool calls. 

Built strictly to the **"Build an RL Environment That Can't Be Broken"** hackathon specification, featuring **dual-container Docker isolation**, **harness-side replay verification**, and **zero-leakage mathematical economic dynamics**.

---

## Key Highlights

- **Anti-Cheat by Design**: Zero code-execution or filesystem tools exposed to the agent. The sandbox runs in an isolated network without internet access. Final scoring is computed on the harness side by replaying the validated action log through an independent engine instance.
- **Pure Standard Library**: Zero third-party Python dependencies in both runtime containers. Clean Docker builds complete in under 30 seconds from scratch.
- **Model-Agnostic**: Compatible with any OpenAI-compatible API (`MODEL`, `API_KEY`, `BASE_URL`). Supports native function calling with automatic text-fallback JSON parsing for models that output structured tool calls in content.
- **Mathematical Economic Depth**: 16 tasks across 3 difficulty tiers (Easy, Medium, Hard) featuring seasonal price cycles, perishability/spoilage, order slippage, compounding loan interest, and theoretical phenomena (Cobweb cycle, Dutch disease, Gresham's law).
- **100% Baseline Verification**: 1,600/1,600 automated gate checks pass across all 16 tasks and 50 random seeds (Reference Solution $\ge 0.95$, No-Op $\le 0.05$).

---

## Quick Start (One Command)

```bash
# 1. Create environment file from template
cp .env.example .env
# Edit .env with your MODEL, API_KEY, BASE_URL

# 2. Run the environment (builds image, runs baselines, then executes model)
docker compose up --build --abort-on-container-exit --exit-code-from harness
```

---

## Interactive Web Testing & Benchmark Studio (GUI)

Rather than running CLI commands, you can launch a local web dashboard to run episodes, monitor gate checks, run Pytest suites, and inspect trajectories:

```bash
# Launch the dashboard (zero external dependencies, pure stdlib)
python scripts/dashboard.py

# Open in your browser:
# http://localhost:8500
```

### Dashboard Capabilities:
- **Episode Studio**: Live visual farm plots, real-time gauges (Day, Cash, Debt, Storage, Score), and live streaming agent actions and tool results.
- **Gate Matrix & Tests**: 1-click verification of all 16 benchmark tasks with live PASS/FAIL status cards, plus 1-click execution of the 50-test Pytest suite with live streamed output.
- **Logs & Trajectories**: Browse previous runs and click **🔍 Inspect** to view detailed step-by-step actions, tool observations, state hashes, and reward components.
- **Submission Packager**: 1-click generation of the official 2-page `design-doc.pdf`, 10-slide `deck.pdf`, and `prple.zip` submission archive.

---

## Project Structure & File Descriptions

```text
├── docker-compose.yml          # Defines isolated sandbox and harness services
├── Dockerfile.harness          # Reproducible build for test harness & evaluator
├── Dockerfile.sandbox          # Hardened build for sandbox server
├── .env.example                # Example environment configuration (no secrets)
├── check_model.py              # Script to verify model credentials
├── README.md                   # Environment documentation & evaluation guide
│
├── simcore/                    # Core Simulation Engine (Shared Module)
│   ├── __init__.py             # Simcore package initialization
│   ├── engine.py               # Deterministic state machine, tool executions, financial logic, scoring
│   └── world.py                # Seeded world generation, 16 task configs, oracle action sequences
│
├── sandbox/                    # Sealed Agent Sandbox
│   └── server.py               # HTTP JSON server executing tools; defense-in-depth typed validation
│
├── harness/                    # Orchestration, Verification & Telemetry
│   ├── __init__.py             # Harness package initialization
│   ├── main.py                 # Container entrypoint supporting MODE=full|all|baselines
│   ├── runner.py               # Episode loop, live stdout streaming, limits, structured telemetry
│   ├── env.py                  # Sandbox client + harness-side replay engine for tamper-proof scoring
│   ├── agents.py               # OpenAI API client with retries + 4 mock agents (solver, idle, chaos, text)
│   ├── tasks.py                # TaskInstance builder and system prompt generation
│   └── tools.py                # 11 JSON function schemas with strict typed argument validation
│
├── inputs/                     # Runtime Instructions & Append Directory
│   ├── README.md               # Explanation of external inputs
│   └── append.txt              # Instructions appended to system prompt during Run B
│
├── tests/                      # Automated Verification & Quality Suite
│   ├── test_gate.py            # Baseline gate check across 16 tasks × 50 seeds
│   ├── test_engine.py          # Unit tests for economic mechanics (taxes, slippage, spoilage, debt)
│   └── test_comprehensive.py   # Integration tests for mocks, edge cases, and parser resilience
│
├── docs/                       # Documentation & Submission Papers
│   ├── design.md               # 2-page system architecture, threat model, and defenses summary
│   └── ECONOMIC_BENCHMARKS.md  # Theoretical foundations for advanced economic benchmark tasks
│
└── scripts/                    # Developer & Utility Scripts
    ├── dashboard.py            # Interactive web studio for testing, gate checks & trajectories
    ├── collect_baseline.sh     # Automates running MODE=baselines and copying gate.json
    ├── generate_pdfs.py        # Compiles 2-page design-doc.pdf and 10-slide deck.pdf
    ├── pack_submission.py      # Validates and packages official prple.zip submission
    └── debugger.py             # Interactive step-debugger and multi-run self-improvement harness
```

---

## Environment Variables (`.env`)

| Variable | Required | Default | Description |
|---|:---:|:---:|---|
| `MODEL` | Yes | `mock/solver` | Model name or mock: `mock/solver`, `mock/idle`, `mock/chaos`, `mock/text` |
| `API_KEY` | Real models | — | LLM provider API key (kept blank in `.env.example`, never committed) |
| `BASE_URL` | Real models | `https://api.openai.com/v1` | OpenAI-compatible endpoint URL |
| `TASK_ID` | No | `farm_seasons` | Task to run (defaults to `farm_seasons` in compose; see task matrix below) |
| `SEED` | No | `0` | Random seed for world generation |
| `MODE` | No | `full` | `full` (single task), `all` (all tasks), `baselines` (gate checks only) |
| `APPEND_FILE` | No | `inputs/append.txt` | Instructions file in `inputs/` appended to system prompt; exits with code 3 if missing |
| `MAX_TOKENS` | No | `4096` | Max completion tokens per request |

---

## Live-Run Exit Codes

| Exit Code | Meaning | Description |
|:---:|:---:|---|
| **0** | Success | Finished successfully with valid score |
| **1** | Crash | Unhandled runtime crash or fatal error |
| **2** | Baseline Failed | Reference solution scored < 0.95 or No-Op scored > 0.05 |
| **3** | Bad Config | Invalid mode, unknown task ID, or missing `APPEND_FILE` |

---

## Tasks & Benchmark Progression

The environment features **5 core economic scenarios** with 2 calibrated difficulty tiers (**Easy**: 14–15 days, 3 plots; **Hard**: 26–30 days, 6 plots), with full backward-compatibility for all legacy aliases:

```bash
# Print all available task IDs and runtime parameters directly from code:
python -c "from simcore.world import TASK_CONFIGS as T; [print(k, v['horizon'], 'days,', v['n_plots'], 'plots') for k, v in T.items()]"
```

| Task ID | Tier | Horizon | Plots | Crops | Key Mechanics |
|---|:---:|:---:|:---:|:---:|---|
| **`farm_seasons`** *(Demo)* | Easy | 14d | 3 | wheat, tomato | Seasonal cycle price waves, storage limits, spoilage decay |
| `seasonal_harvest_easy` | Easy | 14d | 3 | wheat, tomato | Core plant $\rightarrow$ harvest $\rightarrow$ sell cycle with perishable storage |
| `seasonal_harvest_hard` | Hard | 28d | 6 | 5 crops | Multi-crop rotation, volatile price waves, 2-day strawberry decay |
| `market_volatility_easy` | Easy | 14d | 3 | wheat, corn | Price elasticity and downward demand slope |
| `market_volatility_hard` | Hard | 30d | 6 | 5 crops | 3.5% marginal slippage, extreme price shocks, saffron deflation |
| `credit_leverage_easy` | Easy | 15d | 3 | wheat, tomato | $50 commercial loan, 3‰ daily interest, Day 14 repayment deadline |
| `credit_leverage_hard` | Hard | 26d | 6 | 5 crops | $100 loan limit, 5‰ compounding interest, Day 20 repayment deadline |
| `climate_shocks_easy` | Easy | 14d | 3 | wheat, corn | Drought announcement with supply contraction |
| `climate_shocks_hard` | Hard | 28d | 6 | 5 crops | Severe mid-season multi-day drought halving all plot yields |
| `commodity_arbitrage_easy` | Easy | 14d | 3 | wheat, radish | Fast capital velocity and short-cycle turnover |
| `commodity_arbitrage_hard` | Hard | 30d | 6 | 5 crops | Hotelling scarcity escalation with warehouse bottlenecks |
| `farm_basic` | Easy | 14d | 3 | wheat | 1-crop baseline agricultural loop |

**Official Demo Task:** `farm_seasons` (alias for `seasonal_harvest_easy`, 14-day horizon)

---

## Tool Space (11 Tools)

Every tool has a typed parameter schema and is enforced in both harness and sandbox:

1. `get_status()` — Inspect day, cash, debt, storage capacity, plot state, and inventory.
2. `get_market(history_days)` — Current crop prices with optional historical trends ($0–7$ days).
3. `get_forecast()` — Deterministic noisy 5-day forward price forecasts.
4. `get_news()` — Announcements regarding upcoming droughts or market spikes.
5. `plant(plot_id, crop)` — Plant a seed on an empty plot (deducts cash immediately).
6. `harvest(plot_id)` — Harvest mature crops into inventory.
7. `sell(crop, quantity)` — Sell inventory at current market price (subject to order slippage).
8. `take_loan(amount_cents)` — Borrow funds up to the credit limit (when loans enabled).
9. `repay(amount_cents)` — Repay outstanding loan balance.
10. `advance_days(n)` — Advance world clock by $n$ days ($1–7$), triggering taxes, interest, and spoilage.
11. `finish()` — Conclude the episode early (remaining days auto-simulate).

---

## Verifier & Reward Formulation

All scoring is deterministic, programmatic, and computed in integer cents:

$$\text{Net Worth} = \text{Cash} + \sum (\text{Inventory Units} \times \text{Floor Price}) - \text{Debt}$$
$$\text{where Floor Price} = 0.50 \times \text{Crop Base Price}$$

$$\text{Gain} = \text{Final Net Worth} - \text{Starting Cash}$$
$$\text{Target} = 0.95 \times \text{Oracle Gain}$$
$$\text{Profit Score} = \text{clamp}\left(\frac{\text{Gain}}{\text{Target}}, 0.0, 1.0\right)$$
$$\text{Debt OK} = 1 \text{ if Debt } == 0 \text{ else } 0$$
$$\text{Total Score} = \text{Profit Score} \times (0.85 + 0.15 \times \text{Debt OK})$$

- **Partial Credit**: Smooth scaling between $0.0$ and $1.0$.
- **Anti-Cheat Floor Price**: Inventory is valued at $50\%$ of base price, preventing hoarded inventory exploits.
- **Tax Drain**: Land taxes apply every day, ensuring idling (no-op) always achieves $\le 0.05$.

---

## Telemetry & Logging

Outputs are written to `./logs/<run_id>/`:
- `episode.jsonl` — Full per-step structured logs (inputs, tool calls, environment responses, state hashes, rewards, latency, tokens).
- `summary.json` — Final outcome, step count, termination reason (`success`, `failure`, `step_cap`, `time_cap`, `crash`), and score breakdown.
- `gate.json` — Pre-run verification results for Reference Solution and No-Op baseline.
