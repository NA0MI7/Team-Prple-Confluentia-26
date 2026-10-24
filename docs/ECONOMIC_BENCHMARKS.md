# Economic Theory Benchmarks: Modeling, Data Dynamics & Learning Specification

This document details the theoretical foundation, data generation mathematics, data quirks, and expected learning trajectories for the 6 advanced economic benchmarks integrated into the Seasonal Farm Market simulation environment.

---

## 1. Overview & Pedagogical Philosophy

In typical language model evaluations, agents achieve high zero-shot baselines ($\ge 0.85$) because the rules are simple, linear, and completely transparent in the system prompt. In such settings, "improvement across runs" is minimal and noisy.

These 6 benchmarks introduce **latent structural phenomena based on foundational economics literature**. 
* **Zero Leakage:** The agent's system prompt and task instructions provide **only factual operational parameters** (cash, plot count, seed cost, grow time). No hints, warnings, or strategy shortcuts are provided.
* **The First-Order Fallacy:** A zero-shot prompt optimizer defaulting to greedy linear decision-making (e.g. buying whatever is currently highest-priced or taking maximal debt) walks directly into an economic trap on **Run 1**, resulting in scores of $\sim 0.20 - 0.40$.
* **Authentic Self-Improvement:** Through post-episode reflection, the AI coach analyzes the financial loss, identifies the structural phenomenon, and extracts durable heuristics. By **Runs 2 and 3**, the agent internalizes the counter-intuitive equilibrium and reaches $\sim 0.85 - 0.95$.

---

## 2. Benchmark Specifications

---

### Benchmark 1: `econ_cobweb_cycle`

#### A. Economic Theory & Background
* **Origin:** *The Cobweb Theorem* (Mordecai Ezekiel, 1938; Nicholas Kaldor, 1934).
* **Phenomenon:** In agricultural markets with production lags, producers make planting decisions based on *current* spot prices. If prices are high today, all regional producers plant that crop simultaneously. When harvests mature several days later, the market suffers an acute supply glut, crashing the price below cost. Meanwhile, the unplanted crop experiences a severe shortage, driving its price skyward.

#### B. Data Generation Model
* **Horizon:** 16 days | **Plots:** 4 | **Starting Cash:** $45.00 | **Land Tax:** $0.20/plot/day ($0.80/day)
* **Crops:**
  * `strawberry`: Seed Cost $3.80 | Grow: 4 days | Yield: 6 units | Base: $3.20 | Spoil: 4 days
  * `wheat`: Seed Cost $1.50 | Grow: 2 days | Yield: 7 units | Base: $1.10 | Spoil: None
* **Price Equation:**
  $$\text{wave}(t) = \cos\left(2\pi \frac{t - 1}{7.5}\right)$$
  $$P_{\text{strawberry}}(t) = P_{\text{base}} \times (1.0 + 0.58 \cdot \text{wave}(t)) \times (1 + \epsilon)$$
  $$P_{\text{wheat}}(t) = P_{\text{base}} \times (1.0 - 0.45 \cdot \text{wave}(t)) \times (1 + \epsilon)$$

#### C. Quirks of the Data
* On Days 1–3, Strawberries trade at peak prices ($\sim \$4.80 - \$5.10$), while Wheat trades at a depressed trough ($\sim \$0.65 - \$0.75$).
* The 5-day noisy forecast on Day 1 shows Strawberries staying lucrative for 1–2 days, creating an irresistible temptation to plant them.
* Exactly when a Day 1 Strawberry planting matures (Day 5), the regional supply wave bottoms out the price to $\sim \$1.30$. Wheat peaks right as Strawberry crashes.

#### D. Naive Agent Failure (Run 1)
* The agent plants all 4 plots with Strawberries on Day 1 (spending $15.20).
* On Day 5, it harvests 24 Strawberries into a flooded market ($1.30/unit). Revenue barely covers seed costs, while 4 days of land taxes ($3.20) wipe out net gains. Score: **$\sim 0.25 - 0.35$**.

#### E. Expected Learned Rule (Run 2+)
* **`[Cobweb Contrarian Planting]`**: *"Do NOT plant crops that are currently at cyclical price peaks on Day 1. Plant counter-cyclical crops (Wheat) whose supply will be scarce at harvest time, and only plant long-cycle crops when their spot prices are currently at a trough."*

---

### Benchmark 2: `econ_dutch_disease`

#### A. Economic Theory & Background
* **Origin:** *The Dutch Disease & The Resource Curse* (W. Max Corden & J. Peter Neary, 1982).
* **Phenomenon:** The discovery and exploitation of an extraordinarily lucrative natural resource or cash crop inflates fixed domestic costs and crowds out baseline diversified industries. When commodity prices mean-revert or crash, the enterprise collapses under its inflated overhead.

#### B. Data Generation Model
* **Horizon:** 16 days | **Plots:** 4 | **Starting Cash:** $50.00 | **Land Tax:** $0.25/plot/day ($1.00/day)
* **Crops:**
  * `saffron`: Seed Cost $4.80 | Grow: 3 days | Yield: 5 units | Base: $3.80 | Spoil: 5 days (Apparent $3.9\times$ revenue multiple)
  * `wheat`: Seed Cost $1.60 | Grow: 2 days | Yield: 8 units | Base: $1.15 | Spoil: None
* **Price Equation:**
  * Days 1–8: $P_{\text{saffron}}(t) = P_{\text{base}} \times (1.15 + 0.12 \sin(1.2t)) \times (1 + \epsilon)$ ($\sim \$4.40 - \$4.80$)
  * Days 9–16: $P_{\text{saffron}}(t) = P_{\text{base}} \times 0.35 \times (1 + \epsilon)$ ($\sim \$1.30$, a structural $-65\%$ collapse)
  * Wheat remains stable and slightly appreciates ($+1.5\%$/day) throughout.

#### C. Quirks of the Data
* Saffron appears so mathematically dominant during the first 8 days that any rational short-term model will allocate 100% of plot capacity to it.
* At Day 9, the market structural collapse is sudden and permanent. If an agent has seeds planted on Day 7 or 8, they mature into an unsellable market where revenue ($5 \times \$1.30 = \$6.50$) cannot even service high land taxes ($4.00$) and seed costs ($4.80$).

#### D. Naive Agent Failure (Run 1)
* The agent monocultures Saffron across all 4 plots continuously. On Day 9 and Day 12, its harvests sell for pennies while daily taxes burn its cash reserve. The agent enters debt or exhausts liquidity before the horizon. Score: **$\sim 0.30 - 0.45$**.

#### E. Expected Learned Rule (Run 2+)
* **`[Dutch Disease Diversification]`**: *"Never monoculture speculative cash crops (Saffron). Maintain at least 50% plot capacity in resilient staple crops (Wheat) to guarantee operational solvency when the high-margin commodity experiences structural deflation."*

---

### Benchmark 3: `econ_liquidity_mismatch`

#### A. Economic Theory & Background
* **Origin:** *Maturity Transformation & Bank Runs* (Douglas Diamond & Philip Dybvig, 1983).
* **Phenomenon:** Funding long-gestation illiquid assets using short-term callable debt creates catastrophic liquidity vulnerability. The borrower can be fundamentally solvent on a balance sheet basis (holding high-value crops in the ground) but gets liquidated due to cash-flow illiquidity at debt maturity.

#### B. Data Generation Model
* **Horizon:** 16 days | **Plots:** 4 | **Starting Cash:** $22.00 (Severely capital constrained)
* **Debt Parameters:** Credit Limit: $60.00 | Daily Interest: $8‰$ (0.8%/day) | **Repayment Deadline: Day 7 Sharp**
* **Crops:**
  * `grape`: Seed Cost $4.50 | Grow: 5 days | Yield: 6 units | Base: $3.50 | Spoil: 6 days (High margin, but 5-day gestation)
  * `radish`: Seed Cost $1.20 | Grow: 2 days | Yield: 7 units | Base: $0.95 | Spoil: None (Fast liquidity turnover)

#### C. Quirks of the Data
* Start cash ($22.00) is barely enough to plant 4 plots of Grapes ($18.00), leaving only $4.00 cash while daily land taxes are $0.80/day ($4.00 in 5 days).
* If the agent takes a bank loan on Day 1 and plants Grapes, the Grapes harvest on Day 6. That leaves exactly 24 hours to harvest, sell into slippage, and repay the debt before the Day 7 deadline. If planting is delayed by even 1 day, the crops are locked in the soil when the bank calls the loan.

#### D. Naive Agent Failure (Run 1)
* The agent borrows $40–$50 and greedily plants Grapes across all plots on Day 2 or 3. When Day 7 arrives, the Grapes are still immature (illiquid). Cash is $0. The debt deadline triggers a 15% net worth penalty and compounding penalty interest. Score: **$\sim 0.20 - 0.35$**.

#### E. Expected Learned Rule (Run 2+)
* **`[Asset-Liability Duration Matching]`**: *"Never fund 5-day crops with a 7-day debt deadline. Use fast 2-day Radish cycles to build liquid equity first, amortize all loan balances before Day 7, and only cultivate long-cycle Grapes once self-funded without debt maturity risk."*

---

### Benchmark 4: `econ_cournot_elasticity`

#### A. Economic Theory & Background
* **Origin:** *Cournot Quantity Competition & Price Elasticity of Demand* (Antoine Augustin Cournot, 1838).
* **Phenomenon:** In shallow markets with downward-sloping demand curves, price is an endogenous function of volume sold. Total revenue ($P \times Q$) peaks at an intermediate quantity; dumping excessive supply beyond the marginal revenue inflection point causes price collapse, yielding less total cash than selling a fraction of the harvest.

#### B. Data Generation Model
* **Horizon:** 15 days | **Plots:** 4 | **Starting Cash:** $45.00 | **Land Tax:** $0.18/plot/day
* **Market Slippage Rate:** **$0.035$ ($3.5\%$ per unit sold in a single transaction)**
* **Crops:**
  * `tomato`: Seed Cost $2.60 | Grow: 3 days | Yield: 10 units | Base: $2.00 | Spoil: 6 days (4 plots = 40 units harvest!)
  * `wheat`: Seed Cost $1.50 | Grow: 2 days | Yield: 6 units | Base: $1.20 | Spoil: None

#### C. Quirks of the Data
* 4 plots of Tomatoes produce 40 units in one harvest.
* With a 3.5% marginal slippage rate and 40% floor price ($0.80/unit):
  * Selling 8 units: Average price $\approx \$1.75 \to \text{Revenue} = \$14.04$
  * Selling 40 units at once: The price slips down to the $40\%$ floor ($0.80/unit) $\to \text{Revenue} \approx \$42.84$ for the 40 units.
  * Selling in 5 daily batches of 8 units: Total revenue $= 5 \times \$14.04 = \mathbf{\$70.20}$ ($+64\%$ more revenue for the exact same harvest).

#### D. Naive Agent Failure (Run 1)
* The agent harvests 40 units and immediately calls `sell(tomato, 40)`. The price collapses to the floor; the agent forfeits over $\$27$ in potential revenue for an entire harvest. Score: **$\sim 0.00 - 0.25$**.

#### E. Expected Learned Rule (Run 2+)
* **`[Quantity Tranche Slicing]`**: *"In high-slippage markets, never liquidate inventory in a single monolithic transaction. Stagger sales into daily tranches of 6 to 8 units to preserve the marginal price curve."*

---

### Benchmark 5: `econ_pigouvian_commons`

#### A. Economic Theory & Background
* **Origin:** *The Economics of Welfare & Pigouvian Externalities* (Arthur C. Pigou, 1920; Garrett Hardin, 1968).
* **Phenomenon:** Heavy private extraction degrades communal resilience. When climatic/environmental shocks occur, over-leveraged and monocultured production models experience catastrophic disruption, whereas diversified systems survive.

#### B. Data Generation Model
* **Horizon:** 16 days | **Plots:** 4 | **Starting Cash:** $45.00 | **Land Tax:** $0.26/plot/day ($1.04/day total)
* **Climatic Shock:** **Severe Drought Event on Days 7 through 10** (announced on Day 5). Halves all harvest yields by $50\%$.
* **Crops:**
  * `tomato`: Seed Cost $3.00 | Grow: 3 days | Yield: 8 units | Base: $2.10 | Spoil: 5 days (High seed cost, high drought exposure)
  * `wheat`: Seed Cost $1.50 | Grow: 2 days | Yield: 7 units | Base: $1.15 | Spoil: 8 days (Low cost, fast 2-day cycle)

#### C. Quirks of the Data
* The Day 1–4 forecast paints Tomatoes as highly profitable, encouraging the agent to commit heavy capital on Day 4.
* The Drought hits Days 7–10: any Tomatoes harvested during this window yield only 4 units instead of 8, turning a projected $\$16.80$ revenue into $\$8.40$, which fails to cover seed ($3.00$) + land tax ($3.12$ over 3 days).
* The 50% drought penalty specifically punishes high-input crops with long maturation windows.

#### D. Naive Agent Failure (Run 1)
* The agent plants Tomatoes on Day 4 and harvests on Day 7 during the drought. Yield is halved, cash reserves are depleted, and high daily taxes ($1.04/day) drain the farm into insolvency. Score: **$\sim 0.30 - 0.45$**.

#### E. Expected Learned Rule (Run 2+)
* **`[Climatic Externality Hedging]`**: *"Check get_news() regularly. When a drought window approaches (Days 7–10), halt expensive 3-day Tomato plantings. Shift to low-cost 2-day Wheat or hold cash reserves until the drought passes."*

---

### Benchmark 6: `econ_hotelling_arbitrage`

#### A. Economic Theory & Background
* **Origin:** *The Economics of Exhaustible Resources* (Harold Hotelling, 1931).
* **Phenomenon:** The market price of a durable, non-perishable asset must appreciate at the rate of interest plus carrying costs. Selling durable assets early for immediate cash sacrifices substantial terminal appreciation value.

#### B. Data Generation Model
* **Horizon:** 16 days | **Plots:** 3 | **Starting Cash:** $42.00 | **Storage Cap:** 80 units
* **Crops:**
  * `corn`: Seed Cost $2.00 | Grow: 3 days | Yield: 9 units | Base: $0.90 | **Spoil: None (100% Durable Store of Value)**
  * `strawberry`: Seed Cost $3.60 | Grow: 3 days | Yield: 5 units | Base: $2.30 | **Spoil: 2 days (Ultra-perishable)**
* **Hotelling Price Dynamic:**
  $$P_{\text{corn}}(t) = P_{\text{base}} \times \left(0.80 + 3.0 \times \left(\frac{t}{16}\right)^{1.85}\right) \times (1 + \epsilon)$$
  * Day 1: $\$0.74$ | Day 5: $\$1.03$ | Day 9: $\$1.65$ | Day 13: $\$2.56$ | Day 15: $\mathbf{\$3.12}$ | Day 16: $\$3.42$
  * Strawberries remain roughly flat ($\sim \$2.30 - \$2.50$).

#### C. Quirks of the Data
* On Days 1–6, Corn looks like an inferior crop compared to Strawberries ($0.90 vs $2.30).
* If the agent plants Corn early, its first harvest on Day 4 sells for a meager $\$0.95/unit$.
* However, Corn has **zero spoilage**. If hoarded in the 80-unit warehouse, its value appreciates to $\$3.12/unit$ on Day 15 and $\$3.42$ on Day 16.

#### D. Naive Agent Failure (Run 1)
* The agent harvests Corn on Day 4 and immediately sells it for $\$0.95$ to realize immediate cash, forfeiting the terminal scarcity surge. Score: **$\sim 0.00 - 0.20$**.

#### E. Expected Learned Rule (Run 2+)
* **`[Intertemporal Hotelling Banking]`**: *"Durable non-perishable crops (Corn) experience late-season price escalation. Do not sell Corn upon harvest in the early game; stockpile it in storage and liquidate at the terminal peak on Days 14–16."*

---

## 3. Empirical Verification & Measured Scores

All economic claims have been empirically verified by executing the naive trap heuristic versus the optimal strategic policy in the live simulation engine (`scripts/verify_economics.py`):

| Benchmark Scenario | Theoretical Phenomenon | Start Cash | Naive Strategy Net Worth | Strategic Solution Net Worth | Naive Score | Strategic Score | Empirical Separation |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `econ_cournot_elasticity` | Marginal Slippage & Output Glut | $45.00 | $32.38 | $377.63 | **0.0000** | **0.9850** | **+0.9850** |
| `econ_cobweb_cycle` | Ezekiel 2-Phase Supply Lag | $45.00 | $61.94 | $346.65 | **0.0067** | **0.9850** | **+0.9783** |
| `econ_liquidity_mismatch` | Maturity Mismatch & Debt Insolvency | $22.00 | -$72.64 | $468.97 | **0.0000** | **0.9850** | **+0.9850** |
| `econ_hotelling_arbitrage` | Scarcity Exhaustion Curve | $50.00 | $1.91 | $101.46 | **0.0000** | **0.9703** | **+0.9703** |
| `econ_dutch_disease` | Corden-Neary Sector Crowding | $40.00 | -$36.05 | $563.28 | **0.0000** | **0.9850** | **+0.9850** |
| `econ_pigouvian_commons` | Hardin Commons & Climate Shock | $45.00 | -$6.70 | $350.35 | **0.0000** | **0.9850** | **+0.9850** |

---

## 4. How to Run & Verify

### Single Task Deep Debugger
```bash
# Inspect turn-by-turn messages, tools, and token metrics on any economic benchmark:
python scripts/debugger.py --task econ_cobweb_cycle --seed 42
python scripts/debugger.py --task econ_dutch_disease --seed 42
python scripts/debugger.py --task econ_liquidity_mismatch --seed 42
```

### Self-Improving Benchmark Mode (Persistent Memory)
```bash
# Run 3 test cases across the Economic Theory Benchmarks suite:
python scripts/debugger.py --self-improve --runs 3 --suite econ

# Run across all 16 combined benchmarks:
python scripts/debugger.py --self-improve --runs 3 --suite all
```
