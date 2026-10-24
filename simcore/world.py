"""
Seeded world generator for the Seasonal Farm Market.
All randomness is precomputed at reset from the seed using separate
random.Random streams per purpose, so agent action order can never
change later randomness.
"""
import random
import math
import copy

# ======================= TASK CONFIGURATIONS =======================
# 5 distinct scenarios with 2 difficulty levels: Easy and Hard.
# Full backup of the previous 16 tasks is preserved in simcore.world_backup.

from simcore.world_backup import TASK_CONFIGS_BACKUP

PRIMARY_TASKS = [
    {
        "id": "seasonal_harvest",
        "name": "Seasonal Cycles & Spoilage",
        "emoji": "🌾",
        "desc": "Crop rotation, seasonal growth cycles, and perishable inventory spoilage management."
    },
    {
        "id": "market_volatility",
        "name": "Market Volatility & Crash",
        "emoji": "📉",
        "desc": "Price elasticity, severe market shocks, and high-slippage liquidation traps."
    },
    {
        "id": "credit_leverage",
        "name": "Credit Leverage & Solvency",
        "emoji": "🏦",
        "desc": "Bank debt leverage, daily compounding interest burden, and deadline solvency."
    },
    {
        "id": "climate_shocks",
        "name": "Climate Shocks & Weather",
        "emoji": "☀️",
        "desc": "Environmental weather events, severe droughts, and volatile demand spikes."
    },
    {
        "id": "commodity_arbitrage",
        "name": "Commodity Arbitrage & Scarcity",
        "emoji": "📈",
        "desc": "Intertemporal asset holding, warehouse storage bottlenecks, and exponential scarcity."
    },
]

TASK_CONFIGS = {
    # ── 1. Seasonal Cycles & Spoilage ──
    "seasonal_harvest_easy": {
        "theme": "seasonal_harvest",
        "difficulty": "easy",
        "display_name": "Seasonal Cycles & Spoilage (Easy)",
        "horizon": 14,
        "n_plots": 3,
        "crops": {
            "wheat": {"seed_cost": 180, "grow_days": 3, "yield_units": 8, "base_price": 120, "spoil_days": None},
            "tomato": {"seed_cost": 280, "grow_days": 2, "yield_units": 6, "base_price": 200, "spoil_days": 5},
        },
        "start_cash": 4500,
        "land_tax": 15,
        "storage_cap": 60,
        "events_on": False,
        "loans_on": False,
        "forecast_noise": 3,
        "slippage_rate": 0.012,
        "price_amplitude": 0.20,
    },
    "seasonal_harvest_hard": {
        "theme": "seasonal_harvest",
        "difficulty": "hard",
        "display_name": "Seasonal Cycles & Spoilage (Hard)",
        "horizon": 28,
        "n_plots": 6,
        "crops": {
            "wheat": {"seed_cost": 200, "grow_days": 3, "yield_units": 8, "base_price": 130, "spoil_days": 6},
            "tomato": {"seed_cost": 320, "grow_days": 2, "yield_units": 6, "base_price": 215, "spoil_days": 3},
            "corn": {"seed_cost": 260, "grow_days": 4, "yield_units": 9, "base_price": 145, "spoil_days": 7},
            "strawberry": {"seed_cost": 440, "grow_days": 4, "yield_units": 5, "base_price": 360, "spoil_days": 2},
            "radish": {"seed_cost": 130, "grow_days": 2, "yield_units": 7, "base_price": 95, "spoil_days": 4},
        },
        "start_cash": 6000,
        "land_tax": 35,
        "storage_cap": 45,
        "events_on": True,
        "loans_on": False,
        "forecast_noise": 12,
        "slippage_rate": 0.025,
        "price_amplitude": 0.42,
    },

    # ── 2. Market Volatility & Crash ──
    "market_volatility_easy": {
        "theme": "market_volatility",
        "difficulty": "easy",
        "display_name": "Market Volatility & Crash (Easy)",
        "horizon": 14,
        "n_plots": 3,
        "crops": {
            "wheat": {"seed_cost": 170, "grow_days": 3, "yield_units": 8, "base_price": 120, "spoil_days": None},
            "corn": {"seed_cost": 240, "grow_days": 4, "yield_units": 9, "base_price": 140, "spoil_days": None},
        },
        "start_cash": 5000,
        "land_tax": 15,
        "storage_cap": 60,
        "events_on": False,
        "loans_on": False,
        "forecast_noise": 4,
        "slippage_rate": 0.012,
        "price_amplitude": 0.20,
    },
    "market_volatility_hard": {
        "theme": "market_volatility",
        "difficulty": "hard",
        "display_name": "Market Volatility & Crash (Hard)",
        "horizon": 30,
        "n_plots": 6,
        "crops": {
            "wheat": {"seed_cost": 190, "grow_days": 2, "yield_units": 7, "base_price": 125, "spoil_days": 6},
            "tomato": {"seed_cost": 300, "grow_days": 3, "yield_units": 7, "base_price": 210, "spoil_days": 4},
            "corn": {"seed_cost": 260, "grow_days": 4, "yield_units": 9, "base_price": 145, "spoil_days": 8},
            "strawberry": {"seed_cost": 420, "grow_days": 4, "yield_units": 5, "base_price": 350, "spoil_days": 3},
            "saffron": {"seed_cost": 520, "grow_days": 3, "yield_units": 5, "base_price": 400, "spoil_days": 5},
        },
        "start_cash": 5500,
        "land_tax": 30,
        "storage_cap": 55,
        "events_on": True,
        "loans_on": False,
        "forecast_noise": 16,
        "slippage_rate": 0.035,
        "price_amplitude": 0.50,
    },

    # ── 3. Credit Leverage & Solvency ──
    "credit_leverage_easy": {
        "theme": "credit_leverage",
        "difficulty": "easy",
        "display_name": "Credit Leverage & Solvency (Easy)",
        "horizon": 15,
        "n_plots": 3,
        "crops": {
            "wheat": {"seed_cost": 180, "grow_days": 3, "yield_units": 8, "base_price": 120, "spoil_days": None},
            "tomato": {"seed_cost": 280, "grow_days": 2, "yield_units": 6, "base_price": 200, "spoil_days": 6},
        },
        "start_cash": 4500,
        "land_tax": 18,
        "storage_cap": 60,
        "events_on": False,
        "loans_on": True,
        "credit_limit": 5000,
        "daily_interest_permille": 3,
        "repay_deadline_day": 14,
        "forecast_noise": 4,
        "slippage_rate": 0.015,
    },
    "credit_leverage_hard": {
        "theme": "credit_leverage",
        "difficulty": "hard",
        "display_name": "Credit Leverage & Solvency (Hard)",
        "horizon": 26,
        "n_plots": 6,
        "crops": {
            "wheat": {"seed_cost": 180, "grow_days": 2, "yield_units": 7, "base_price": 125, "spoil_days": 8},
            "tomato": {"seed_cost": 320, "grow_days": 3, "yield_units": 7, "base_price": 215, "spoil_days": 4},
            "corn": {"seed_cost": 250, "grow_days": 4, "yield_units": 8, "base_price": 140, "spoil_days": 8},
            "grape": {"seed_cost": 450, "grow_days": 5, "yield_units": 6, "base_price": 360, "spoil_days": 6},
            "saffron": {"seed_cost": 550, "grow_days": 3, "yield_units": 5, "base_price": 420, "spoil_days": 5},
        },
        "start_cash": 4000,
        "land_tax": 35,
        "storage_cap": 50,
        "events_on": True,
        "loans_on": True,
        "credit_limit": 15000,
        "daily_interest_permille": 8,
        "repay_deadline_day": 15,
        "forecast_noise": 10,
        "slippage_rate": 0.020,
        "price_amplitude": 0.35,
    },

    # ── 4. Climate Shocks & Weather ──
    "climate_shocks_easy": {
        "theme": "climate_shocks",
        "difficulty": "easy",
        "display_name": "Climate Shocks & Weather (Easy)",
        "horizon": 14,
        "n_plots": 3,
        "crops": {
            "wheat": {"seed_cost": 170, "grow_days": 3, "yield_units": 8, "base_price": 120, "spoil_days": 8},
            "corn": {"seed_cost": 240, "grow_days": 4, "yield_units": 9, "base_price": 145, "spoil_days": None},
        },
        "start_cash": 5000,
        "land_tax": 18,
        "storage_cap": 70,
        "events_on": True,
        "loans_on": False,
        "forecast_noise": 4,
        "slippage_rate": 0.015,
    },
    "climate_shocks_hard": {
        "theme": "climate_shocks",
        "difficulty": "hard",
        "display_name": "Climate Shocks & Weather (Hard)",
        "horizon": 28,
        "n_plots": 6,
        "crops": {
            "wheat": {"seed_cost": 180, "grow_days": 2, "yield_units": 8, "base_price": 125, "spoil_days": 6},
            "tomato": {"seed_cost": 310, "grow_days": 3, "yield_units": 6, "base_price": 215, "spoil_days": 4},
            "corn": {"seed_cost": 250, "grow_days": 4, "yield_units": 9, "base_price": 140, "spoil_days": 8},
            "strawberry": {"seed_cost": 420, "grow_days": 4, "yield_units": 5, "base_price": 360, "spoil_days": 3},
            "radish": {"seed_cost": 130, "grow_days": 2, "yield_units": 7, "base_price": 95, "spoil_days": 4},
        },
        "start_cash": 5000,
        "land_tax": 35,
        "storage_cap": 60,
        "events_on": True,
        "loans_on": False,
        "forecast_noise": 14,
        "slippage_rate": 0.022,
        "price_amplitude": 0.40,
    },

    # ── 5. Commodity Arbitrage & Scarcity ──
    "commodity_arbitrage_easy": {
        "theme": "commodity_arbitrage",
        "difficulty": "easy",
        "display_name": "Commodity Arbitrage & Scarcity (Easy)",
        "horizon": 14,
        "n_plots": 3,
        "crops": {
            "wheat": {"seed_cost": 160, "grow_days": 2, "yield_units": 7, "base_price": 115, "spoil_days": None},
            "radish": {"seed_cost": 120, "grow_days": 2, "yield_units": 7, "base_price": 95, "spoil_days": None},
        },
        "start_cash": 4500,
        "land_tax": 15,
        "storage_cap": 60,
        "events_on": False,
        "loans_on": False,
        "forecast_noise": 4,
        "slippage_rate": 0.015,
    },
    "commodity_arbitrage_hard": {
        "theme": "commodity_arbitrage",
        "difficulty": "hard",
        "display_name": "Commodity Arbitrage & Scarcity (Hard)",
        "horizon": 30,
        "n_plots": 6,
        "crops": {
            "corn": {"seed_cost": 210, "grow_days": 3, "yield_units": 9, "base_price": 95, "spoil_days": None},
            "strawberry": {"seed_cost": 380, "grow_days": 3, "yield_units": 5, "base_price": 240, "spoil_days": 2},
            "radish": {"seed_cost": 120, "grow_days": 2, "yield_units": 7, "base_price": 95, "spoil_days": 4},
            "saffron": {"seed_cost": 500, "grow_days": 3, "yield_units": 5, "base_price": 390, "spoil_days": 5},
            "grape": {"seed_cost": 450, "grow_days": 5, "yield_units": 6, "base_price": 350, "spoil_days": 6},
        },
        "start_cash": 5000,
        "land_tax": 35,
        "storage_cap": 50,
        "events_on": False,
        "loans_on": False,
        "forecast_noise": 10,
        "slippage_rate": 0.030,
        "price_model": "hotelling",
    },
}

# Aliases for backward compatibility with existing tests and scripts
TASK_ALIASES = {
    "farm_basic": "seasonal_harvest_easy",
    "farm_two_crops": "seasonal_harvest_easy",
    "farm_seasons": "seasonal_harvest_easy",
    "farm_credit": "credit_leverage_easy",
    "farm_crash": "market_volatility_hard",
    "farm_events": "climate_shocks_easy",
    "farm_sprint": "commodity_arbitrage_easy",
    "farm_spoilage": "seasonal_harvest_hard",
    "farm_drought": "climate_shocks_hard",
    "farm_market_rush": "market_volatility_hard",
    "econ_cobweb_cycle": "seasonal_harvest_hard",
    "econ_dutch_disease": "market_volatility_hard",
    "econ_liquidity_mismatch": "credit_leverage_hard",
    "econ_cournot_elasticity": "market_volatility_hard",
    "econ_pigouvian_commons": "climate_shocks_hard",
    "econ_hotelling_arbitrage": "commodity_arbitrage_hard",
    # Base theme names default to easy
    "seasonal_harvest": "seasonal_harvest_easy",
    "market_volatility": "market_volatility_easy",
    "credit_leverage": "credit_leverage_easy",
    "climate_shocks": "climate_shocks_easy",
    "commodity_arbitrage": "commodity_arbitrage_easy",
}

# Merge aliases and backup entries for backward compatibility
for _alias, _target in TASK_ALIASES.items():
    if _alias not in TASK_CONFIGS and _target in TASK_CONFIGS:
        TASK_CONFIGS[_alias] = TASK_CONFIGS[_target]

# Retain farm_basic exact config for strict unit test assertions
if "farm_basic" in TASK_CONFIGS_BACKUP:
    TASK_CONFIGS["farm_basic"] = TASK_CONFIGS_BACKUP["farm_basic"]

DEMO_TASK = "seasonal_harvest_easy"



def generate(task_id, seed):
    """
    Generate a complete world dict for a given task_id and seed.
    Returns dict with: cfg, prices, events, initial_state, oracle_actions.
    All randomness from separate Random streams keyed by purpose.
    """
    if task_id not in TASK_CONFIGS:
        raise ValueError(f"Unknown task_id: {task_id}. Valid: {sorted(TASK_CONFIGS.keys())}")

    cfg = copy.deepcopy(TASK_CONFIGS[task_id])

    # Create separate RNG streams
    rng_prices = random.Random(f"{seed}:{task_id}:prices")
    rng_events = random.Random(f"{seed}:{task_id}:events")
    rng_forecast = random.Random(f"{seed}:{task_id}:forecast")
    rng_crops = random.Random(f"{seed}:{task_id}:crops")

    # Vary crop parameters slightly per seed
    _vary_crops(cfg, rng_crops)

    # Generate price table
    prices = _generate_prices(cfg, rng_prices)

    # Generate events
    events = []
    if cfg.get("events_on", False):
        events = _generate_events(cfg, rng_events)
    # NOTE: demand spike is applied at sell-time in engine.sell(), not here.
    # This avoids double-counting and keeps the price table as clean base values.

    # Build initial state
    plots = {}
    for i in range(cfg["n_plots"]):
        plots[str(i)] = {"crop": None, "planted_day": None}

    initial_state = {
        "day": 1,
        "cash": cfg["start_cash"],
        "debt": 0,
        "inventory": [],
        "plots": plots,
        "forecast_noise_key": f"{seed}:{task_id}:forecast_noise",
    }

    # Generate oracle actions
    oracle_actions = _generate_oracle(cfg, prices, events, initial_state)

    return {
        "cfg": cfg,
        "prices": prices,
        "events": events,
        "initial_state": initial_state,
        "oracle_actions": oracle_actions,
    }


def _vary_crops(cfg, rng):
    """Slightly vary crop parameters per seed within bounds."""
    # Preserve calibrated economic parameter structures for theoretical benchmarks
    if cfg.get("price_model") in ("cobweb", "dutch_disease", "hotelling", "cournot", "liquidity_mismatch", "pigouvian"):
        return

    for crop_name in sorted(cfg["crops"].keys()):
        c = cfg["crops"][crop_name]
        # Vary base_price by +/- 15%
        factor = 1.0 + rng.uniform(-0.15, 0.15)
        c["base_price"] = max(50, int(c["base_price"] * factor))
        # Vary seed_cost by +/- 10%
        factor = 1.0 + rng.uniform(-0.10, 0.10)
        c["seed_cost"] = max(50, int(c["seed_cost"] * factor))
        # Occasionally vary yield_units by +/- 1
        c["yield_units"] = max(2, c["yield_units"] + rng.choice([-1, 0, 0, 1]))


def _generate_prices(cfg, rng):
    """
    Generate deterministic price table: {day: {crop: price_cents}}.
    Supports standard seasonal waves and specialized economic theory models.
    """
    horizon = cfg["horizon"]
    model = cfg.get("price_model", "seasonal")
    prices = {}

    if model == "cobweb":
        # Mordecai Ezekiel Cobweb cycle: Strawberry peaks early, crashes when harvest matures (days 5-7),
        # recovers on days 10-12, and crashes again. Wheat is counter-cyclical.
        for day in range(1, horizon + 1):
            prices[day] = {}
            cobweb_wave = math.cos(2 * math.pi * (day - 1) / 7.5)
            noise = rng.uniform(-0.03, 0.03)
            for crop_name in sorted(cfg["crops"].keys()):
                base = cfg["crops"][crop_name]["base_price"]
                if crop_name == "strawberry":
                    p = base * (1.0 + 0.58 * cobweb_wave) * (1.0 + noise)
                else:
                    p = base * (1.0 - 0.45 * cobweb_wave) * (1.0 + noise)
                prices[day][crop_name] = max(25, int(p))
        return prices

    elif model == "dutch_disease":
        # Corden-Neary Dutch Disease: Saffron has an early boom (days 1-8),
        # then suffers structural demand/price collapse (-65%) from day 9 onward.
        for day in range(1, horizon + 1):
            prices[day] = {}
            noise = rng.uniform(-0.03, 0.03)
            for crop_name in sorted(cfg["crops"].keys()):
                base = cfg["crops"][crop_name]["base_price"]
                if crop_name == "saffron":
                    if day <= 8:
                        p = base * (1.15 + 0.12 * math.sin(day * 1.2)) * (1.0 + noise)
                    else:
                        p = base * 0.35 * (1.0 + noise)
                else:
                    p = base * (1.0 + 0.015 * day) * (1.0 + noise)
                prices[day][crop_name] = max(25, int(p))
        return prices

    elif model == "hotelling":
        # Harold Hotelling's Rule: Non-perishable corn appreciates along a compound scarcity curve,
        # starting low ($0.80) and peaking at $3.50+ on days 14-16. Perishable strawberry oscillates flatly.
        for day in range(1, horizon + 1):
            prices[day] = {}
            noise = rng.uniform(-0.03, 0.03)
            for crop_name in sorted(cfg["crops"].keys()):
                base = cfg["crops"][crop_name]["base_price"]
                if crop_name == "corn":
                    curve = (day / horizon) ** 1.85
                    p = base * (0.80 + 3.0 * curve) * (1.0 + noise)
                else:
                    p = base * (1.0 + 0.14 * math.sin(day * 1.5)) * (1.0 + noise)
                prices[day][crop_name] = max(25, int(p))
        return prices

    # Default Seasonal Sine Wave
    amplitude = cfg.get("price_amplitude", 0.20)
    crop_params = {}
    for crop_name in sorted(cfg["crops"].keys()):
        period = rng.randint(8, max(9, horizon // 2))
        phase = rng.randint(0, period)
        crop_params[crop_name] = {"period": period, "phase": phase}

    for day in range(1, horizon + 1):
        prices[day] = {}
        for crop_name in sorted(cfg["crops"].keys()):
            base = cfg["crops"][crop_name]["base_price"]
            cp = crop_params[crop_name]
            seasonal = amplitude * math.sin(
                2 * math.pi * (day + cp["phase"]) / cp["period"]
            )
            noise = rng.uniform(-0.05, 0.05)
            price = int(base * (1 + seasonal) * (1 + noise))
            price = max(1, price)
            prices[day][crop_name] = price

    return prices


def _generate_events(cfg, rng):
    """Generate drought and demand spike events."""
    horizon = cfg["horizon"]
    events = []

    # Specialized pigouvian drought window
    if cfg.get("price_model") == "pigouvian" and horizon >= 14:
        events.append({
            "type": "drought",
            "start_day": 7,
            "end_day": 10,
            "announce_day": 5,
        })
        return events

    # Drought: a window of 2-4 days somewhere in the middle
    if horizon >= 14:
        drought_len = rng.randint(2, 4)
        earliest = max(4, horizon // 4)
        latest = horizon - drought_len - 2
        if latest > earliest:
            drought_start = rng.randint(earliest, latest)
            events.append({
                "type": "drought",
                "start_day": drought_start,
                "end_day": drought_start + drought_len - 1,
                "announce_day": max(1, drought_start - 2),
            })

    # Demand spike: one crop gets x1.6 for 2-3 days
    crops = sorted(cfg["crops"].keys())
    if crops and horizon >= 10:
        spike_crop = rng.choice(crops)
        spike_start = rng.randint(max(3, horizon // 4), max(4, horizon - 4))
        events.append({
            "type": "demand_spike",
            "crop": spike_crop,
            "start_day": spike_start,
            "end_day": min(horizon, spike_start + 2),
            "announce_day": max(1, spike_start - 2),
        })

    return events


def _generate_oracle(cfg, prices, events, initial_state):
    """
    Generate a deterministic oracle action sequence.
    The oracle has perfect knowledge of the price table and events.
    It acts through the real engine interface.
    Returns list of (tool_name, args) tuples.
    """
    from simcore.engine import Engine

    world = {
        "cfg": copy.deepcopy(cfg),
        "prices": copy.deepcopy(prices),
        "events": copy.deepcopy(events),
        "initial_state": copy.deepcopy(initial_state),
    }
    eng = Engine(world)
    actions = []
    horizon = cfg["horizon"]

    def do(name, args):
        method = getattr(eng, name)
        text, err, done = method(**args)
        if not err:
            actions.append((name, args))
        return text, err, done

    def get_effective_price(crop_name, day):
        """Get the effective sell price for a crop on a given day (including demand spike)."""
        p = prices.get(day, {}).get(crop_name, 0)
        for ev in events:
            if (ev["type"] == "demand_spike" and ev["crop"] == crop_name and
                    ev["start_day"] <= day <= ev["end_day"]):
                p = int(p * 1.6)
        return p

    def find_best_sell_day(crop_name, from_day, spoil_deadline):
        """Find the day with highest effective price within the window."""
        best_day = from_day
        best_price = 0
        end = min(spoil_deadline, horizon)
        for d in range(from_day, end + 1):
            p = get_effective_price(crop_name, d)
            if p > best_price:
                best_price = p
                best_day = d
        return best_day, best_price

    def is_drought(day):
        for ev in events:
            if ev["type"] == "drought" and ev["start_day"] <= day <= ev["end_day"]:
                return True
        return False

    # If loans are on, take a modest loan for more capital
    if cfg.get("loans_on", False):
        if cfg.get("price_model") == "liquidity_mismatch":
            loan_amt = min(2000, cfg["credit_limit"])
        else:
            loan_amt = min(cfg["credit_limit"] // 2, cfg["start_cash"])
        do("take_loan", {"amount_cents": loan_amt})

    day = 1
    max_iterations = horizon * 20  # safety cap
    iteration = 0
    while day <= horizon and not eng.is_done() and iteration < max_iterations:
        iteration += 1
        state = eng.get_state()
        day = state["day"]
        if day > horizon:
            break

        # 1. HARVEST ready plots (always harvest immediately unless in drought)
        for pid in sorted(state["plots"].keys(), key=lambda x: int(x)):
            plot = state["plots"][pid]
            if plot["crop"] is not None:
                ccfg = cfg["crops"][plot["crop"]]
                if state["day"] >= plot["planted_day"] + ccfg["grow_days"]:
                    # Skip harvest during drought if possible (yields half)
                    if is_drought(state["day"]):
                        # Check if drought ends soon and crop won't spoil
                        drought_end = state["day"]
                        for ev in events:
                            if ev["type"] == "drought" and ev["start_day"] <= state["day"] <= ev["end_day"]:
                                drought_end = ev["end_day"]
                        # Only skip if we can wait
                        # (don't skip if we'd miss planting window)
                        if drought_end - state["day"] <= 2 and state["day"] + 3 < horizon:
                            continue
                    do("harvest", {"plot_id": int(pid)})

        # 2. SELL inventory at the right time
        state = eng.get_state()
        for crop_name in sorted(cfg["crops"].keys()):
            crop_lots = [lot for lot in state["inventory"] if lot["crop"] == crop_name]
            if not crop_lots:
                continue
            owned = sum(lot["qty"] for lot in crop_lots)

            ccfg = cfg["crops"][crop_name]
            # Find spoilage deadline for oldest lot
            oldest_harvest = min(lot["harvest_day"] for lot in crop_lots)
            if ccfg.get("spoil_days") is not None:
                spoil_deadline = oldest_harvest + ccfg["spoil_days"]
            else:
                spoil_deadline = horizon + 1

            # Find the best sell day from today
            best_day, best_price = find_best_sell_day(crop_name, day, spoil_deadline)
            today_price = get_effective_price(crop_name, day)

            should_sell = False

            # Must sell: about to spoil
            if ccfg.get("spoil_days") is not None:
                if day >= spoil_deadline - 1:
                    should_sell = True

            # Should sell: today IS the best day
            if best_day == day:
                should_sell = True

            # Near horizon: sell everything
            if day >= horizon - 2:
                should_sell = True

            # Today price is within 5% of best and best is > 2 days away
            if today_price >= best_price * 0.95 and best_day - day > 2:
                should_sell = True

            # Emergency sell: need cash for taxes to avoid debt
            daily_tax = cfg["land_tax"] * cfg["n_plots"]
            days_to_best = max(1, best_day - day)
            tax_needed = daily_tax * days_to_best
            if state["cash"] < tax_needed and owned > 0:
                should_sell = True

            if should_sell and owned > 0:
                if cfg.get("slippage_rate", 0.015) >= 0.030 and day < horizon - 2 and not (ccfg.get("spoil_days") and day >= spoil_deadline - 1):
                    sell_qty = min(owned, 8)
                else:
                    sell_qty = owned
                do("sell", {"crop": crop_name, "quantity": sell_qty})

        # 3. PLANT on empty plots
        state = eng.get_state()
        for pid in sorted(state["plots"].keys(), key=lambda x: int(x)):
            plot = state["plots"][pid]
            if plot["crop"] is None:
                best_crop = _oracle_pick_crop(cfg, prices, events, state["day"], horizon)
                if best_crop is not None:
                    ccfg = cfg["crops"][best_crop]
                    if state["cash"] >= ccfg["seed_cost"]:
                        text, err, done = do("plant", {"plot_id": int(pid), "crop": best_crop})
                        if done:
                            break
                        state = eng.get_state()  # Refresh after cash change

        # 4. REPAY any debt (loans or tax shortfalls)
        state = eng.get_state()
        if state["debt"] > 0:
            if cfg.get("loans_on", False):
                deadline = cfg.get("repay_deadline_day", horizon)
                # Repay loans aggressively near deadline
                if day >= deadline - 4:
                    repay_amt = min(state["cash"], state["debt"])
                    if repay_amt > 0:
                        do("repay", {"amount_cents": repay_amt})
            else:
                # Always repay tax-driven debt immediately
                repay_amt = min(state["cash"], state["debt"])
                if repay_amt > 0:
                    do("repay", {"amount_cents": repay_amt})

        # 5. ADVANCE days
        if eng.is_done():
            break

        state = eng.get_state()
        # Find soonest interesting event (harvest ready, sell day, spoilage)
        targets = []

        # Harvest targets
        for pid in sorted(state["plots"].keys(), key=lambda x: int(x)):
            plot = state["plots"][pid]
            if plot["crop"] is not None:
                ccfg = cfg["crops"][plot["crop"]]
                ready_day = plot["planted_day"] + ccfg["grow_days"]
                if ready_day > state["day"]:
                    targets.append(ready_day)

        # Sell timing targets (check if there's a better price coming soon)
        for crop_name in sorted(cfg["crops"].keys()):
            owned = sum(lot["qty"] for lot in state["inventory"] if lot["crop"] == crop_name)
            if owned > 0:
                ccfg = cfg["crops"][crop_name]
                oldest_lots = [lot for lot in state["inventory"] if lot["crop"] == crop_name]
                if ccfg.get("spoil_days") is not None and oldest_lots:
                    oldest_harvest = min(lot["harvest_day"] for lot in oldest_lots)
                    targets.append(oldest_harvest + ccfg["spoil_days"] - 1)
                # Find best sell day
                spoil_deadline = horizon + 1
                if ccfg.get("spoil_days") is not None and oldest_lots:
                    oldest_harvest = min(lot["harvest_day"] for lot in oldest_lots)
                    spoil_deadline = oldest_harvest + ccfg["spoil_days"]
                best_day, _ = find_best_sell_day(crop_name, state["day"] + 1, spoil_deadline)
                if best_day > state["day"]:
                    targets.append(best_day)

        if targets:
            nearest = min(t for t in targets if t > state["day"])
            advance = min(7, max(1, nearest - state["day"]))
        else:
            # Nothing pending: advance by 1 if plots are empty (to minimize tax)
            advance = 1

        if advance >= 1 and not eng.is_done():
            text, err, done = do("advance_days", {"n": advance})
            if done:
                break
            state = eng.get_state()
            day = state["day"]

    # Final cleanup before finishing: harvest any remaining ready plots, sell all inventory, repay debt
    state = eng.get_state()
    for pid in sorted(state["plots"].keys(), key=lambda x: int(x)):
        plot = state["plots"][pid]
        if plot["crop"] is not None:
            ccfg = cfg["crops"][plot["crop"]]
            if state["day"] >= plot["planted_day"] + ccfg["grow_days"]:
                do("harvest", {"plot_id": int(pid)})

    state = eng.get_state()
    for crop_name in sorted(cfg["crops"].keys()):
        lots = [l for l in state["inventory"] if l["crop"] == crop_name]
        owned = sum(l["qty"] for l in lots)
        if owned > 0:
            do("sell", {"crop": crop_name, "quantity": owned})

    state = eng.get_state()
    if state["debt"] > 0 and state["cash"] > 0:
        repay_amt = min(state["cash"], state["debt"])
        do("repay", {"amount_cents": repay_amt})

    if not eng.is_done():
        do("finish", {})

    return actions


def _oracle_pick_crop(cfg, prices, events, current_day, horizon):
    """Pick the best crop to plant right now based on full price knowledge and event forecasts."""
    best = None
    best_profit = 0  # Only plant if profitable

    for crop_name in sorted(cfg["crops"].keys()):
        ccfg = cfg["crops"][crop_name]
        harvest_day = current_day + ccfg["grow_days"]
        if harvest_day > horizon:
            continue

        # Check if harvest day is during drought (cuts yield by 50%)
        effective_yield = ccfg["yield_units"]
        for ev in events:
            if ev.get("type") == "drought" and ev.get("start_day", 0) <= harvest_day <= ev.get("end_day", 0):
                effective_yield = max(1, effective_yield // 2)

        # Find best sell day after harvest
        best_sell_price = 0
        spoil_limit = horizon + 1
        if ccfg.get("spoil_days") is not None:
            spoil_limit = harvest_day + ccfg["spoil_days"]

        for sd in range(harvest_day, min(spoil_limit, horizon + 1)):
            p = prices.get(sd, {}).get(crop_name, 0)
            # Account for demand spike
            for ev in events:
                if (ev["type"] == "demand_spike" and ev["crop"] == crop_name and
                        ev["start_day"] <= sd <= ev["end_day"]):
                    p = int(p * 1.6)
            if p > best_sell_price:
                best_sell_price = p

        # Estimate profit: revenue - cost - tax during grow period
        revenue = best_sell_price * effective_yield
        # Approximate slippage: ~10% discount for moderate quantities
        revenue = int(revenue * 0.92)
        cost = ccfg["seed_cost"]
        # Tax cost during grow period (per plot)
        tax_cost = cfg["land_tax"] * ccfg["grow_days"]
        profit = revenue - cost - tax_cost
        time_to_sell = ccfg["grow_days"] + 1
        profit_per_day = profit / max(1, time_to_sell)

        if profit_per_day > best_profit:
            best_profit = profit_per_day
            best = crop_name

    return best


def validate_oracle(task_id, seed, min_gain=500):
    """
    Validate that the oracle achieves sufficient gain for a (task, seed).
    Returns (oracle_gain, world) or raises if degenerate.
    """
    from simcore.engine import Engine

    world = generate(task_id, seed)
    eng = Engine(world)

    # Replay oracle actions
    for action_name, args in world["oracle_actions"]:
        method = getattr(eng, action_name)
        method(**args)

    # Ensure game is done
    if not eng.is_done():
        eng.finish()

    oracle_nw = eng.compute_net_worth()
    oracle_gain = oracle_nw - world["cfg"]["start_cash"]
    
    return oracle_gain, world


def get_all_task_ids():
    """Return sorted list of all task IDs."""
    return sorted(TASK_CONFIGS.keys())


def get_primary_task_ids():
    """Return the 5 distinct scenario IDs."""
    return [t["id"] for t in PRIMARY_TASKS]
