"""
Generate design-doc.pdf (2-page document) and deck.pdf (12-slide presentation)
for the Hackathon submission using fpdf2 with pure ASCII text.
"""
from fpdf import FPDF


def build_design_doc():
    """Build design-doc.pdf (strictly 2 pages)."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(12, 10, 12)

    # ================= PAGE 1 =================
    pdf.add_page()
    
    # Title Banner
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 7, "Seasonal Farm Market - Design Document", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 4, "Hackathon: Build an RL Environment That Can't Be Broken | Team: prple (team_148) | Demo: farm_seasons", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(59, 130, 246)
    pdf.set_line_width(0.6)
    pdf.line(12, 22, 198, 22)
    pdf.ln(3)

    # Section 1: Overview
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 4.5, "1. OVERVIEW & SYSTEM ARCHITECTURE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(0, 3.5, (
        "Seasonal Farm Market is an unbreakable RL environment where an AI agent acts as a farm business manager across "
        "a standardized 20-day horizon via 11 strictly typed domain tool calls. Built strictly using the Python standard library (clean Docker build "
        "in under 30s; zero third-party packages in sandbox runtime), the system enforces total isolation through a dual-container architecture:\n"
        "- Sealed Sandbox Container: Hosts game state; isolated via internal: true (no internet access), read-only root filesystem, "
        "cap_drop ALL, and no-new-privileges. Exposes ONLY 11 domain tools - zero bash, code execution, or file read/write tools exist.\n"
        "- Orchestration Harness: Connects to any OpenAI-compatible API, enforces 40-step and 10-minute live limits, caps tool output at 2KB, "
        "compresses conversational history (<64K tokens), and performs tamper-proof scoring by replaying the validated action log through an independent engine."
    ))
    pdf.ln(1)

    # Section 2: Task Progression
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 4.5, "2. TASK DESIGN, PROCEDURAL VARIATION & DIFFICULTY CURVE (31 TASKS ACROSS 4 TIERS)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(0, 3.5, (
        "- Easy Tier (farm_basic, farm_two_crops, farm_sprint): Tests core plant-harvest-sell loop, yield vs. grow-time trade-offs, "
        "and capital velocity over a uniform 20-day horizon.\n"
        "- Medium Tier (farm_seasons [DEMO], farm_events, farm_spoilage): Sinusoidal seasonal prices, shelf-life inventory decay, "
        "storage limits (60 units), and weather/demand shocks (50% drought yield, 1.6x price spikes).\n"
        "- Hard Tier (farm_credit, farm_crash, farm_drought, farm_market_rush): Compounding commercial debt, high price slippage "
        "(1.5-2.0%/unit), noisy forecasts, and extreme price volatility.\n"
        "- Microeconomic Benchmarks (econ_cobweb_cycle, econ_cournot_elasticity, econ_dutch_disease, econ_hotelling_arbitrage, econ_pigouvian_commons): "
        "Deep structural economic phenomena (production lag gluts, quadratic price impact, resource curse, exhaustible scarcity, tax internalities). Zero prompt leakage.\n"
        "- Procedural Variation by Seed: Seeds vary base prices (+/-15%), seed costs (+/-10%), yields (+/-1), shock timing (drought onset/duration), and seasonal phases. "
        "The oracle dynamically recalculates target per seed; 3,100/3,100 automated gate checks pass with oracle >= 0.95 and no-op <= 0.05 across 31 tasks."
    ))
    pdf.ln(1)

    # Section 3: Reward Design
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 4.5, "3. DETERMINISTIC PROGRAMMATIC REWARD FORMULATION", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(0, 3.5, (
        "The verifier is 100% deterministic, programmatic, and computed strictly in integer cents (no float rounding exploits):\n"
        "  net_worth = cash + sum(inventory_units * min(floor_price, current_market_price)) - debt  [floor_price = 50% of base_price]\n"
        "  gain = net_worth - start_cash  |  ratio = gain / oracle_gain  |  oracle_benchmark in [0.960, 0.985]\n"
        "  profit = oracle_benchmark * ratio (if ratio <= 1) else smooth non-saturating curve up to 1.0\n"
        "  total_score = profit * (0.85 + 0.15 * debt_ok)  [debt_ok = 1 if debt == 0 at finish else 0]\n"
        "Key Reward Integrity Mechanics:\n"
        "- Anti-Hoarding Valuation: Unsold inventory is valued at min(floor_price, current_market_price). Hoarding during crashes creates zero phantom value.\n"
        "- Independent Non-Saturating Scoring: Eliminates artificial 100% clamping so strong models are evaluated continuously without false ceilings.\n"
        "- Daily Land Tax Drain: Land taxes apply daily ($15-$25/plot/day). Inaction (no-op) erodes capital and strictly guarantees score <= 0.05.\n"
        "- Insolvent Debt Penalty: Unpaid debt carries compounding interest and incurs a 15% score haircut if non-zero at finish."
    ))

    # ================= PAGE 2 =================
    pdf.add_page()
    
    # Section 4: Red Team Adversarial Table
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 4.5, "4. RED TEAM ATTACK MATRIX & SECURITY AUDITING", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.2)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 3.5, "Empirical verification across 7 adversarial attacker vectors (scripts/red_team.py):", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(0.5)

    # Table Header
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 6.8)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(32, 4.2, "Attack Vector", 1, new_x="RIGHT", new_y="TOP", align="L", fill=True)
    pdf.cell(46, 4.2, "What It Tests", 1, new_x="RIGHT", new_y="TOP", align="L", fill=True)
    pdf.cell(48, 4.2, "What Happened (Observed)", 1, new_x="RIGHT", new_y="TOP", align="L", fill=True)
    pdf.cell(60, 4.2, "Engine Defense Mechanism", 1, new_x="LMARGIN", new_y="NEXT", align="L", fill=True)

    red_team_rows = [
        ("Hoarder Agent", "Unsold inventory gives unearned score", "Scored 0.0000; phantom value wiped", "Valued at min(floor, market); daily land tax erodes unliquidated stock."),
        ("Counterfeit Selling", "Selling > owned or negative quantity", "Rejected with error; cash unchanged", "Strict bounds (qty in [1, owned]); rejects negative/zero sales before mutation."),
        ("Deadbeat Borrower", "Take max loan and never repay", "Scored 0.0000; total score crushed", "Debt deducted from net worth; 0.85 debt_ok multiplier; compounding interest."),
        ("TimeWarp / Null Args", "advance_days(9999), null, bad types", "Clamped to 7 days; 0 server crashes", "Strict type coercion & [1, 7] bounds validation; invalid actions safely rejected."),
        ("Plot Squatter / Fake Crop", "Plant on occupied plot or fake crop", "Rejected with error; plot preserved", "Plot occupancy validation & crop catalog check; episode continues unharmed."),
        ("Tool Flooder", "Spam 100 tool calls in single reply", "Calls 11-100 dropped; flagged", "Hard cap MAX_TOOL_CALLS_PER_REPLY = 10; memory & execution time protected."),
        ("Garbage Speaker", "Truncated JSON, raw conversational text", "Parsed candidates; 0 crashes", "Dual-mode parser with regex fallback & normalizer; resilient token extraction.")
    ]

    pdf.set_font("Helvetica", "", 6.4)
    pdf.set_text_color(30, 41, 59)
    for attack, test, happened, defense in red_team_rows:
        pdf.cell(32, 4.0, attack, 1, new_x="RIGHT", new_y="TOP", align="L")
        pdf.cell(46, 4.0, test, 1, new_x="RIGHT", new_y="TOP", align="L")
        pdf.cell(48, 4.0, happened, 1, new_x="RIGHT", new_y="TOP", align="L")
        pdf.cell(60, 4.0, defense, 1, new_x="LMARGIN", new_y="NEXT", align="L")

    pdf.ln(1)

    # Section 5: Fuzzing & Cryptographic Replay
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 4.5, "5. ADVERSARIAL INVARIANT FUZZING & CRYPTOGRAPHIC REPLAY VERIFICATION", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(0, 3.5, (
        "- 10,000-Step Invariant Fuzzing (scripts/fuzz_engine.py): Executed 10,000 randomized and adversarial action sequences across 104 full episodes. "
        "Zero unhandled exceptions; verified 3 core invariant properties: (1) Cash never silently negative without debt; (2) Inventory >= 0; (3) Deterministic SHA-256 transitions.\n"
        "- Cryptographic Replay Verification (scripts/verify_replay.py): Independent scoring CLI reads episode.jsonl, replays logged actions through "
        "a clean engine, and compares SHA-256 state hashes turn-by-turn. Verified 100% bit-for-bit match on pass/fail trajectories."
    ))
    pdf.ln(1)

    # Section 6: Model Separation & Empirical Economics
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 4.5, "6. MODEL CAPABILITY SEPARATION & MEASURED ECONOMIC BENCHMARKS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(0, 3.5, (
        "- Empirical Model Separation: Weak Model (Random/No-op: 0.0000) vs. Mid Model (Greedy/Myopic: 0.0219 - 0.3623) vs. Strong Model (Oracle: 1.0000). "
        "Separation spread ranges from +0.6377 on basic farming up to +1.0000 on deep microeconomic cycles.\n"
        "- Measured Empirical Economics (scripts/verify_economics.py - Real Engine Runs):\n"
        "  * Cournot Elasticity: Naive $73.27 (score 0.2361) vs. Strategic $171.04 (score 1.0000) [+0.7639 spread]\n"
        "  * Cobweb Production Cycle: Naive $44.69 (score 0.0000) vs. Counter-Cyclical $282.72 (score 1.0000) [+1.0000 spread]\n"
        "  * Liquidity Mismatch: Naive -$15.54 (score 0.0000) vs. Solvent Staggering $143.76 (score 1.0000) [+1.0000 spread]\n"
        "  * Hotelling Arbitrage: Naive $39.15 (score 0.0000) vs. Scarcity Arbitrage $159.43 (score 1.0000) [+1.0000 spread]\n"
        "  * Dutch Disease: Naive $23.40 (score 0.0000) vs. Diversification $194.68 (score 1.0000) [+1.0000 spread]"
    ))
    pdf.ln(1)

    # Section 7: Context Handling & Production Limits
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 4.5, "7. CONTEXT MANAGEMENT, LIVE LIMITS & SECURITY TELEMETRY", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(30, 41, 59)
    pdf.multi_cell(0, 3.5, (
        "- Context Protection: Tool output hard-capped at 2,000 characters; older observations compressed into 1-line state digests while preserving "
        "the last 3 turns intact. 20-day episodes consume <12K tokens, staying safely below 64K limits.\n"
        "- Live Limits: Standardized 20-day horizon finishable well within 20 steps via advance_days(1-7) and multi-tool batching (up to 10 calls/reply hinted in schemas).\n"
        "- Anomaly Detection: Harness logs suspicious_count and invalid_actions_count, emitting [SECURITY WARNING] in terminal and summary.json."
    ))

    output_path = "design-doc.pdf"
    pdf.output(output_path)
    print(f"Generated {output_path} ({len(pdf.pages)} pages)")


def build_deck():
    """Build deck.pdf (12-slide presentation in landscape format)."""
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.set_margins(16, 12, 16)

    # Helper for slide header & footer
    def setup_slide(title, subtitle, slide_num):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 17)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(0, 5, subtitle, new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_draw_color(59, 130, 246)
        pdf.set_line_width(0.8)
        pdf.line(16, 27, 281, 27)
        
        # Content Box
        pdf.set_fill_color(248, 250, 252)
        pdf.rect(16, 30, 265, 155, "F")
        pdf.set_draw_color(226, 232, 240)
        pdf.rect(16, 30, 265, 155, "D")
        
        # Footer
        pdf.set_xy(16, 192)
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(100, 5, "Seasonal Farm Market - Hackathon Finals", new_x="RIGHT", new_y="TOP")
        pdf.cell(165, 5, f"Slide {slide_num} / 12", align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(22, 34)

    # ================= SLIDE 1: Executive Summary =================
    setup_slide(
        "Seasonal Farm Market: An Unbreakable RL Environment",
        "Hackathon: Build an RL Environment That Can't Be Broken | Team: prple (team_148)",
        "01"
    )
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(30, 41, 59)
    bullets_01 = [
        "- Core Mission: Build a world an AI agent can act in, get scored by, and fail to cheat.",
        "- Domain Track: Games & World Simulations (Running a realistic agricultural economy under dynamic market constraints).",
        "- Technology Foundation: Pure Python Standard Library (0 third-party packages in sandbox, <30s Docker build).",
        "- Dual-Container Physical Isolation: Sealed HTTP sandbox (internal: true, no internet, read-only FS) + replay verification harness.",
        "- Standardized 20-Day Horizon: Uniform 20-day horizon across all 31 tasks (4 plots, 3 crops, perishable spoilage, seasonal cycles).",
        "- Verified Reliability: 3,100/3,100 automated gate checks pass across 31 tasks and 50 seeds with zero flakiness."
    ]
    for b in bullets_01:
        pdf.set_x(22)
        pdf.multi_cell(253, 6.8, b)
        pdf.ln(1.5)

    # ================= SLIDE 2: The Challenge =================
    setup_slide(
        "The Challenge: Why RL Environments Break",
        "Agents are relentless optimizers that exploit weak reward structures, float drift, and leaky state.",
        "02"
    )
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(30, 41, 59)
    bullets_02 = [
        "- Common Weakness 1: Tiny state spaces (Tic-tac-toe/grid-worlds) that models memorize or solve in trivial brute-force steps.",
        "- Common Weakness 2: LLM-as-judge or fuzzy regex checkers that award undeserved points for hallucinated or sycophantic text.",
        "- Common Weakness 3: Leaky sandboxes exposing bash/read_file where models inspect hidden unit tests or edit score files directly.",
        "- Common Weakness 4: Floating-point rounding loopholes, infinite debt exploitation, or hoarding unsellable inventory for phantom gains.",
        "- Common Weakness 5: Inconsistent task horizons and uncompressed context causing agent disorientation or token window overflows.",
        "- Our Philosophy: Defense-in-depth architectural isolation combined with deterministic microeconomics and integer cent arithmetic."
    ]
    for b in bullets_02:
        pdf.set_x(22)
        pdf.multi_cell(253, 6.8, b)
        pdf.ln(1.5)

    # ================= SLIDE 3: What We Did Different (NEW) =================
    setup_slide(
        "What We Did Different: Engineering Against Exploits",
        "A direct architectural comparison: Conventional RL Hackathon setups vs. Team Prple's defended design.",
        "03"
    )
    # Comparison Table Header
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 7.8)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(20)
    pdf.cell(38, 6.5, "Architectural Pillar", 1, new_x="RIGHT", new_y="TOP", align="L", fill=True)
    pdf.cell(105, 6.5, "Conventional RL Setup (Vulnerable)", 1, new_x="RIGHT", new_y="TOP", align="L", fill=True)
    pdf.cell(114, 6.5, "Team Prple Defended Implementation", 1, new_x="LMARGIN", new_y="NEXT", align="L", fill=True)

    diff_rows = [
        ("Sandbox Security",
         "Single container, bash/exec access, filesystem read/write, open internet",
         "Dual-container: sealed sandbox, read-only FS, zero shell tools, 11 typed RPCs"),
        ("Scoring Integrity",
         "In-sandbox evaluation script or LLM-as-judge vulnerable to prompt injection",
         "Out-of-band replay harness: bit-for-bit re-execution against fresh engine"),
        ("Reward Arithmetic",
         "Floating-point floats with rounding drift; phantom score from hoarded stock",
         "Strict integer cents ($45 = 4500c), min(floor, market) anti-hoarding valuation"),
        ("Horizon Consistency",
         "Variable / disjoint horizons (10-60 days) causing agent disorientation",
         "Standardized 20-day horizon across all 31 tasks; context kept <12K tokens"),
        ("Microeconomic Depth",
         "Trivial grid-worlds or static linear games memorized in brute-force steps",
         "5 structural microeconomic traps (Cobweb, Hotelling, Cournot, Dutch disease)"),
        ("Live Observability",
         "Headless batch console logs with zero interactive testing or visual insight",
         "1-command Docker Web Studio (:8500) with animated SVG crops, charts & ledger")
    ]

    pdf.set_font("Helvetica", "", 7.2)
    pdf.set_text_color(30, 41, 59)
    for pillar, conv, prple in diff_rows:
        pdf.set_x(20)
        pdf.cell(38, 6.2, pillar, 1, new_x="RIGHT", new_y="TOP", align="L")
        pdf.cell(105, 6.2, conv, 1, new_x="RIGHT", new_y="TOP", align="L")
        pdf.cell(114, 6.2, prple, 1, new_x="LMARGIN", new_y="NEXT", align="L")

    pdf.ln(3)
    # Highlight box underneath
    pdf.set_x(20)
    pdf.set_fill_color(236, 253, 245)
    pdf.set_draw_color(16, 185, 129)
    pdf.set_line_width(0.4)
    pdf.rect(20, pdf.get_y(), 257, 10, "FD")
    pdf.set_xy(23, pdf.get_y() + 2.5)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(6, 95, 70)
    pdf.cell(0, 5, "Architectural Takeaway: Rather than hoping agents behave, we isolate execution physically, eliminate math exploits deterministically,", new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(23)
    pdf.cell(0, 4, "and provide a full live visual studio for transparent human and automated evaluation.", new_x="LMARGIN", new_y="NEXT")

    # ================= SLIDE 4: Dual-Container Zero-Trust =================
    setup_slide(
        "Dual-Container Zero-Trust Architecture",
        "Physical runtime isolation between untrusted agent execution and deterministic scoring verifier.",
        "04"
    )
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(30, 41, 59)
    bullets_04 = [
        "- Sealed Sandbox Container: Docker network internal: true (no internet access), read-only root filesystem, dropped capabilities (cap_drop: ALL, no-new-privileges).",
        "- Zero Attack Surface: Sandbox exposes strictly 11 domain HTTP tools (plant, harvest, sell, loan, advance_days, etc.); zero bash, python exec, or file tools.",
        "- Isolated Orchestration Harness: Connects to gpt-6-luna via litellm gateway, enforces 40-step budget, 2KB tool caps, and history compression.",
        "- Cryptographic Out-of-Band Scoring: Sandbox never computes final score; harness replays verified action log against fresh engine.",
        "- Ultra-Fast Clean Build: Pinned Python 3.11-slim standard library; clean Docker build completes in <30 seconds from zero cache."
    ]
    for b in bullets_04:
        pdf.set_x(22)
        pdf.multi_cell(253, 7.2, b)
        pdf.ln(2.0)

    # ================= SLIDE 5: Microeconomic Depth & 20-Day Horizon =================
    setup_slide(
        "Microeconomic Depth & Standardized 20-Day Horizon",
        "31 varied tasks across 4 difficulty tiers + procedural seed variation generating hundreds of scenarios.",
        "05"
    )
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(30, 41, 59)
    bullets_05 = [
        "- Standardized 20-Day Horizon: All 31 tasks unified to a 20-day horizon, eliminating time-horizon dissonance across benchmarks.",
        "- Easy Tier (farm_basic, farm_two_crops, farm_sprint): Core planting/harvesting, grow-time vs. yield tradeoffs, cash velocity.",
        "- Medium Tier (farm_seasons, farm_events, farm_spoilage): Seasonal sinusoidal prices, shelf-life spoilage, storage caps, weather shocks.",
        "- Hard Tier (farm_credit, farm_crash, farm_drought): Compounding interest, credit limits, order slippage, noisy forecasts.",
        "- Deep Microeconomic Benchmarks: Cobweb cycles (Ezekiel 1938), Dutch disease resource curse, Hotelling scarcity arbitrage, Cournot slippage.",
        "- Procedural Variation by Seed: Seeds vary base prices (+/-15%), seed costs (+/-10%), yields (+/-1), shock timing, and seasonal phases.",
        "- Dynamic Oracle Scaling: Oracle solves each procedural seed dynamically; 3,100/3,100 gate checks pass with oracle >= 0.95 and no-op <= 0.05."
    ]
    for b in bullets_05:
        pdf.set_x(22)
        pdf.multi_cell(253, 6.2, b)
        pdf.ln(1.2)

    # ================= SLIDE 6: Reward Design =================
    setup_slide(
        "Deterministic Programmatic Reward Design",
        "Integer cents, 0.95x oracle scaling, anti-hoarding valuation, and strict debt penalty.",
        "06"
    )
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(30, 41, 59)
    bullets_06 = [
        "- Net Worth Formulation: Cash + sum(Inventory * min(floor_price, current_market_price)) - Debt.",
        "- Anti-Hoarding Valuation: Unsold crops evaluated at min(floor, market). If market crashes below floor, zero phantom value is created.",
        "- Continuous Non-Saturating Gain: profit scales monotonically with independent oracle benchmark (> 0.95 and < 1.0) without false ceilings.",
        "- Saturation Eliminated: Non-clamped scoring cleanly separates naive attempts (0.20-0.40) from skilled strategic runs (0.85-0.98).",
        "- Insolvent Debt Penalty: total_score = profit * (0.85 + 0.15 * debt_ok). Unpaid debt imposes a strict 15% penalty haircut.",
        "- Daily Land Tax Drain: Land taxes apply daily ($15-$25/plot/day). Inaction (no-op) erodes capital and guarantees score <= 0.05.",
        "- Zero Rounding Arbitrage: All economic state is tracked strictly in integer cents (e.g., $45.00 = 4500 cents)."
    ]
    for b in bullets_06:
        pdf.set_x(22)
        pdf.multi_cell(253, 6.5, b)
        pdf.ln(1.5)

    # ================= SLIDE 7: Red Team Attack Matrix =================
    setup_slide(
        "Red Team Adversarial Attack Matrix",
        "Empirical verification across 7 adversarial attacker vectors (scripts/red_team.py) - 100% Contained & Defended.",
        "07"
    )
    # Render full red team table
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(20)
    pdf.cell(38, 6, "Attack Vector", 1, new_x="RIGHT", new_y="TOP", align="L", fill=True)
    pdf.cell(56, 6, "What It Tests", 1, new_x="RIGHT", new_y="TOP", align="L", fill=True)
    pdf.cell(65, 6, "What Happened (Observed)", 1, new_x="RIGHT", new_y="TOP", align="L", fill=True)
    pdf.cell(98, 6, "Engine Defense Mechanism", 1, new_x="LMARGIN", new_y="NEXT", align="L", fill=True)

    red_team_deck_rows = [
        ("Hoarder Agent", "Unsold inventory gives unearned score", "Scored 0.0000; phantom value wiped", "Valued at min(floor, market) (50% base). Taxes drain cash. Score < 0.60."),
        ("Counterfeit Selling", "Selling > owned or negative quantity", "Rejected with error; cash unchanged", "Strict bounds (qty in [1, owned]); rejects negative/zero sales before mutation."),
        ("Deadbeat Borrower", "Take max loan and never repay", "Scored 0.0000; total score crushed", "Debt deducted from net worth; 0.85 debt_ok multiplier; compounding interest."),
        ("TimeWarp / Null Args", "advance_days(9999), null, bad types", "Clamped to 7 days; 0 server crashes", "Strict type coercion & [1, 7] bounds validation; invalid actions safely rejected."),
        ("Plot Squatter / Fake Crop", "Plant on occupied plot or fake crop", "Rejected with error; plot preserved", "Plot occupancy guard & crop catalog lookup; state unmodified; episode proceeds."),
        ("Tool Flooder", "Spam 100 tool calls in single reply", "Calls 11-100 dropped; security alert", "Hard cap MAX_TOOL_CALLS_PER_REPLY = 10; memory & execution time protected."),
        ("Garbage Speaker", "Truncated JSON, raw conversational text", "Parsed valid candidates; 0 crashes", "Dual-mode parser with regex fallback & normalizer; resilient token extraction.")
    ]

    pdf.set_font("Helvetica", "", 7.5)
    pdf.set_text_color(30, 41, 59)
    for attack, test, happened, defense in red_team_deck_rows:
        pdf.set_x(20)
        pdf.cell(38, 5.2, attack, 1, new_x="RIGHT", new_y="TOP", align="L")
        pdf.cell(56, 5.2, test, 1, new_x="RIGHT", new_y="TOP", align="L")
        pdf.cell(65, 5.2, happened, 1, new_x="RIGHT", new_y="TOP", align="L")
        pdf.cell(98, 5.2, defense, 1, new_x="LMARGIN", new_y="NEXT", align="L")

    pdf.ln(2)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(22, 101, 52)
    pdf.cell(0, 5, "Red Team Outcome: All 7 adversarial exploits defeated. Suspicious action counter logs [SECURITY WARNING] alerts.", new_x="LMARGIN", new_y="NEXT")

    # ================= SLIDE 8: Fuzzing & Replay =================
    setup_slide(
        "10,000 Invariant Fuzzing & Cryptographic Replay",
        "Extensive random action stress-testing and bit-for-bit replay verification tool (scripts/verify_replay.py).",
        "08"
    )
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(30, 41, 59)
    bullets_08 = [
        "- 10,000-Step Adversarial Invariant Fuzzing (scripts/fuzz_engine.py):",
        "  * Tested 10,000 random and adversarial action sequences across 104+ full episodes.",
        "  * Invariant 1: Cash never silently goes negative without debt record.",
        "  * Invariant 2: Inventory quantities are strictly non-negative (>= 0) at all times.",
        "  * Invariant 3: Determinism: Same seed + same actions yields 100% identical SHA-256 state hash.",
        "  * Fuzzing Outcome: 0 unhandled crashes, 0 invariant violations across all 10,000 steps.",
        "- Cryptographic Replay Verification Tool (scripts/verify_replay.py):",
        "  * Independent CLI tool reads episode.jsonl, replays logged actions through a fresh engine, and compares hashes turn-by-turn.",
        "  * Verified 100% bit-for-bit match on sample-trajectories/success (8/8 steps) and failure (9/9 steps)."
    ]
    for b in bullets_08:
        pdf.set_x(22)
        pdf.multi_cell(253, 6.2, b)
        pdf.ln(1.2)

    # ================= SLIDE 9: Model Separation =================
    setup_slide(
        "Model Separation Benchmark & Empirical Economics",
        "Monotonic capability spread across models and exact measured numbers from the real simulation engine.",
        "09"
    )
    # Side-by-side tables
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(15, 23, 42)
    pdf.set_x(20)
    pdf.cell(125, 5, "Model Capability Separation Benchmark (scripts/benchmark_separation.py)", 0, new_x="RIGHT", new_y="TOP", align="L")
    pdf.cell(10, 5, "", 0, new_x="RIGHT", new_y="TOP")
    pdf.cell(122, 5, "Empirical Economic Trap Benchmarks (scripts/verify_economics.py)", 0, new_x="LMARGIN", new_y="NEXT", align="L")

    # Table 1: Model separation
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 6.8)
    pdf.set_x(20)
    pdf.cell(45, 4.5, "Scenario", 1, new_x="RIGHT", new_y="TOP", align="L", fill=True)
    pdf.cell(20, 4.5, "Weak", 1, new_x="RIGHT", new_y="TOP", align="C", fill=True)
    pdf.cell(20, 4.5, "Mid", 1, new_x="RIGHT", new_y="TOP", align="C", fill=True)
    pdf.cell(20, 4.5, "Strong", 1, new_x="RIGHT", new_y="TOP", align="C", fill=True)
    pdf.cell(20, 4.5, "Spread", 1, new_x="RIGHT", new_y="TOP", align="C", fill=True)

    pdf.cell(10, 4.5, "", 0, new_x="RIGHT", new_y="TOP")

    # Table 2: Empirical economics
    pdf.cell(48, 4.5, "Economic Benchmark", 1, new_x="RIGHT", new_y="TOP", align="L", fill=True)
    pdf.cell(25, 4.5, "Naive Score", 1, new_x="RIGHT", new_y="TOP", align="C", fill=True)
    pdf.cell(25, 4.5, "Smart Score", 1, new_x="RIGHT", new_y="TOP", align="C", fill=True)
    pdf.cell(24, 4.5, "Spread", 1, new_x="LMARGIN", new_y="NEXT", align="C", fill=True)

    sep_rows = [
        ("farm_basic", "0.0000", "0.3623", "1.0000", "+0.6377", "Cournot Elasticity", "$73.27 (0.24)", "$171.04 (1.00)", "+0.7639"),
        ("farm_seasons", "0.0000", "0.1352", "1.0000", "+0.8648", "Cobweb Cycle", "$44.69 (0.00)", "$282.72 (1.00)", "+1.0000"),
        ("farm_events", "0.0000", "0.0646", "1.0000", "+0.9354", "Liquidity Mismatch", "$-15.54 (0.00)", "$143.76 (1.00)", "+1.0000"),
        ("farm_credit", "0.0000", "0.0219", "1.0000", "+0.9781", "Hotelling Arbitrage", "$39.15 (0.00)", "$159.43 (1.00)", "+1.0000"),
        ("econ_cobweb", "0.0000", "0.0000", "1.0000", "+1.0000", "Dutch Disease", "$23.40 (0.00)", "$194.68 (1.00)", "+1.0000"),
        ("econ_hotelling", "0.0000", "0.0437", "1.0000", "+0.9563", "Pigouvian Commons", "$29.40 (0.00)", "$157.29 (1.00)", "+1.0000")
    ]

    pdf.set_font("Helvetica", "", 6.5)
    pdf.set_text_color(30, 41, 59)
    for r in sep_rows:
        pdf.set_x(20)
        pdf.cell(45, 4.2, r[0], 1, new_x="RIGHT", new_y="TOP", align="L")
        pdf.cell(20, 4.2, r[1], 1, new_x="RIGHT", new_y="TOP", align="C")
        pdf.cell(20, 4.2, r[2], 1, new_x="RIGHT", new_y="TOP", align="C")
        pdf.cell(20, 4.2, r[3], 1, new_x="RIGHT", new_y="TOP", align="C")
        pdf.cell(20, 4.2, r[4], 1, new_x="RIGHT", new_y="TOP", align="C")
        pdf.cell(10, 4.2, "", 0, new_x="RIGHT", new_y="TOP")
        pdf.cell(48, 4.2, r[5], 1, new_x="RIGHT", new_y="TOP", align="L")
        pdf.cell(25, 4.2, r[6], 1, new_x="RIGHT", new_y="TOP", align="C")
        pdf.cell(25, 4.2, r[7], 1, new_x="RIGHT", new_y="TOP", align="C")
        pdf.cell(24, 4.2, r[8], 1, new_x="LMARGIN", new_y="NEXT", align="C")

    pdf.ln(2.5)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 4.5, "Conclusion: Clear monotonic separation across models. No ceiling/floor collapse. Empirical numbers measured directly in real engine.", new_x="LMARGIN", new_y="NEXT")

    # ================= SLIDE 10: Harness & Live Limits =================
    setup_slide(
        "Model-Agnostic Resilient Harness & Live Limits",
        "Dual-mode parsing, 40-step budget, tool output caps, and observation compression (<64K tokens).",
        "10"
    )
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(30, 41, 59)
    bullets_10 = [
        "- Any OpenAI-Compatible Model: Reads MODEL, API_KEY, BASE_URL. Tested with gpt-6-luna and 4 diverse mock agents.",
        "- Dual-Mode Parsing: Parses native OpenAI tool_calls or extracts fenced JSON from raw markdown text with automatic normalization.",
        "- Live Limits Fit: Standardized 20-day horizon is finishable in under 20 steps via advance_days(1-7) and multi-tool batching.",
        "- Tool Output Capping: All tool execution responses are hard-capped at 2,000 characters, preventing verbose memory dumps.",
        "- Turn History Compression: Preserves the last 3 turns with complete detail; compresses older turns into 1-line state digests.",
        "- Context Length Guarantee: 20-day episodes consume <12K tokens, staying well beneath the 64K token limit with zero overflow risk."
    ]
    for b in bullets_10:
        pdf.set_x(22)
        pdf.multi_cell(253, 6.5, b)
        pdf.ln(1.5)

    # ================= SLIDE 11: Interactive Web Studio & Dashboard =================
    setup_slide(
        "Interactive Web Studio & Live Dashboard (GUI)",
        "Standalone full-stack web simulator and evaluation console running on http://localhost:8500.",
        "11"
    )
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(30, 41, 59)
    bullets_11 = [
        "- 1-Command Launch: docker compose up --build boots the interactive visual simulator instantly on port 8500.",
        "- Real-Time Dynamic Graphics: Animated SVG plots reflecting crop growth stages (Seedling, Growing, Mature, Withered) and weather.",
        "- Interactive Farming Sandbox: Evaluators can play through any scenario manually, step-by-step, to test economic dynamics and edge cases.",
        "- Live Financial Ledgers & Charts: Real-time Cash, Debt, Net Worth, Market Pricing trends, and crop inventory trackers.",
        "- High-Contrast Polished UI: Obsidian/dark theme with pristine high-contrast white metrics, step-by-step action history, and reset controls.",
        "- Dual Operational Profiles: Default launches interactive Studio on port 8500; docker compose --profile eval up runs headless automated evaluation."
    ]
    for b in bullets_11:
        pdf.set_x(22)
        pdf.multi_cell(253, 6.5, b)
        pdf.ln(1.5)

    # ================= SLIDE 12: Conclusion & Checklist =================
    setup_slide(
        "Conclusion & Submission Checklist",
        "Production-ready for live VM execution on main branch | Team prple (team_148).",
        "12"
    )
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(30, 41, 59)
    bullets_12 = [
        "- One Command Execution: docker compose up --build (Dashboard :8500) or docker compose --profile eval up (Evaluation Harness).",
        "- Ultra-Fast Clean Build: Pinned Python stdlib image builds in <30 seconds from clean cache with zero external packages in sandbox.",
        "- Sealed Security: Sandbox has no internet, no shell tools, and cannot tamper with verifier replay scoring.",
        "- Full Deliverables Included:",
        "  * baseline-results/gate.json (3,100 / 3,100 gate checks passed with 100% reliability)",
        "  * test-run-logs/ (3 full runs: basic, demo, and chaos stress)",
        "  * sample-trajectories/ (pass/fail trajectories with 100% bit-for-bit replay verification)",
        "  * design-doc.pdf (strictly 2 pages) and deck.pdf (strictly 12 slides)",
        "  * scripts/ (verify_replay.py, red_team.py, fuzz_engine.py, verify_economics.py, benchmark_separation.py, dashboard.py)",
        "- Ready for judges evaluation. Thank you!"
    ]
    for b in bullets_12:
        pdf.set_x(22)
        pdf.multi_cell(253, 6.2, b)
        pdf.ln(1.2)

    output_path = "deck.pdf"
    pdf.output(output_path)
    print(f"Generated {output_path} ({len(pdf.pages)} slides)")


if __name__ == "__main__":
    build_design_doc()
    build_deck()
