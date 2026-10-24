# Design Document — Seasonal Farm Market

## Overview

The Seasonal Farm Market is an RL environment for LLM agents. The agent manages a small farm economy through tool calls, making decisions about planting, harvesting, selling, and timing over a multi-day horizon. A deterministic programmatic verifier scores the agent's final net worth gain against a scripted oracle.

## Task & Reward Design

### Task Progression (6 tasks, 3 difficulty levels)

1. **farm_basic** (easy): Single crop, short horizon. Tests basic plant→harvest→sell loop.
2. **farm_two_crops** (easy): Two crops with different economics. Tests crop selection.
3. **farm_seasons** (medium): Seasonal price swings + spoilage. Tests timing and inventory management.
4. **farm_events** (medium): Drought and demand spike events. Tests information use and adaptation.
5. **farm_credit** (hard): Loans with daily compounding interest and repayment deadline. Tests capital management.
6. **farm_crash** (hard): Noisy forecasts, tight storage, stronger slippage. Tests robustness under uncertainty.

### Reward Design

The scoring formula uses **relative performance against a scripted oracle**:

```
profit = clamp(gain / (0.95 × oracle_gain), 0, 1)
debt_ok = 1 if no debt at end, else 0
total = profit × (0.85 + 0.15 × debt_ok)
```

Key design choices:
- **0.95× oracle target**: Requires high-precision economic execution against the verified oracle solver.
- **Conservative inventory valuation (50% of base price)**: Prevents agents from gaming the score by hoarding inventory that would be hard to actually sell. Only realized cash is fully valued.
- **Debt penalty (15% multiplicative)**: Incentivizes clean financial management without making debt catastrophic.
- **No additive free points**: No-op always scores ≤ 0 because daily taxes erode the starting cash.
- **Integer cents everywhere**: Eliminates floating-point rounding exploits.

### Difficulty Curve Validation

Tests verify:
- Greedy agent (plant cheapest, sell immediately) scores ≤ 0.7 on hard tasks
- Random agent averages ≤ 0.35 across 20 seeds
- Oracle scores ≥ 0.95 across 50 seeds
- No-op scores ≤ 0.05 across 50 seeds

## Anti-Cheat Reasoning

### 1. No Code Execution Tools

The sandbox exposes ONLY the 11 game tools. There are no `list_files`, `read_file`, `write_file`, `run_python`, or code execution tools. This eliminates:
- Direct reward spoofing (writing to score files)
- Hidden test case extraction
- Sandbox escape via arbitrary code execution
- Network access from within the sandbox

### 2. Replay-Based Scoring

The harness maintains its **own engine instance** and an ordered log of accepted state-changing actions. Final scoring **replays the action log through a fresh harness engine from the seeded start**. This means:
- A compromised sandbox cannot forge scores
- State hash comparison after each step detects divergence
- Divergence is flagged in telemetry for audit

### 3. Deterministic World Generation

All randomness is precomputed at reset from the seed using **separate `random.Random` streams per purpose**:
- `f"{seed}:{task_id}:prices"` for price generation
- `f"{seed}:{task_id}:events"` for event generation
- `f"{seed}:{task_id}:forecast"` for forecast noise
- `f"{seed}:{task_id}:crops"` for crop parameter variation

This ensures:
- Same (task_id, seed) always produces identical worlds
- Agent action order cannot influence future randomness
- Iteration is always in sorted order (no dict/set ordering accidents)

### 4. Integer Money

All monetary values are integer cents. This prevents:
- Floating-point accumulation errors
- Rounding exploits
- Epsilon-based arbitrage

### 5. Deterministic Forecast Noise

Forecast noise is a deterministic function of `(seed, crop, target_day)` computed via SHA-256 hash. Repeated `get_forecast()` calls on the same day return **identical values**, preventing:
- Noise averaging by spamming forecasts
- Information extraction beyond what the noise function reveals

### 6. Conservative Inventory Valuation

Floor price for inventory = 50% of base price. This prevents:
- Hoarding large inventory to inflate net worth
- Growing crops with no intent to sell

### 7. Sandbox Hardening

Docker security measures:
- `read_only: true` filesystem
- `tmpfs` for `/tmp` (size-limited)
- `cap_drop: ALL` (no Linux capabilities)
- `no-new-privileges` security option
- `cpus: "1.0"` resource limit
- `pids: 64` process limit
- `mem_limit: 512M`
- Internal-only network (no internet access)
- No published ports

## Known Weaknesses

1. **Oracle is greedy, not optimal**: The scripted oracle uses a heuristic strategy. A sufficiently clever agent could theoretically outperform it, causing `profit > 1.0` (clamped to 1.0). This is by design — we want a "good enough" bar, not a perfect one.

2. **Slippage model is simple**: The linear slippage (1.5% per unit) is a simplification. A more realistic model would use order book depth. However, the simple model is transparent and exploitable only by selling in small batches across days (which is the intended strategy).

3. **Price model is predictable**: Sinusoidal prices with noise are somewhat predictable with enough history. This is intentional — the environment rewards agents that learn to read market patterns.

4. **No multi-agent dynamics**: Prices aren't affected by agent actions (except slippage). This simplifies the environment but means there's no strategic interaction.

## Defenses Summary

| Threat | Defense |
|--------|---------|
| Reward spoofing | No code execution tools; replay scoring |
| Hidden case leaking | No file access tools |
| Sandbox escape | Read-only filesystem; cap_drop ALL; no-new-privileges |
| Float exploits | Integer cents everywhere |
| Forecast gaming | Deterministic noise function (no averaging) |
| Score inflation via inventory | Conservative 50% valuation |
| Random seed manipulation | Precomputed separate RNG streams |
| State tampering | Hash comparison; replay from fresh engine |
| Denial of service | Resource limits; pids limit; timeout per tool call |
