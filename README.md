# No-Limit Pokerbots

An archive of eight iterations of tournament pokerbot submissions built for the No-Limit Bot Building Tournament hosted by Sequoia Capital, Citadel Securities, and OpenAI.

The project targets an eight-player no-limit hold'em variant with a five-card flop auction, ICM-based tournament scoring, strict per-action latency (sub-1ms), and no persistent cross-table memory. Each directory under [`bots/`](bots/) is a complete historical submission containing:

- `agent.py` — the tournament SDK entry point and selected strategy mode;
- `core.py` — betting, auction, equity, ICM, and action-safety logic;
- `policy.json` — precomputed starting-hand and auction lookup data.

## Iteration history

The folders use portfolio-friendly names. The original archive names are retained here for traceability.

| # | Readable name | Original archive | Mode | What changed |
|---:|---|---|---|---|
| 1 | [`mathematical-baseline`](bots/01-mathematical-baseline/) | `level1-verified.zip` | `LEVEL_1` | Conservative mathematical baseline with fixed opening ranges, ICM-aware calls, precomputed hand strength, and flop-auction valuation. |
| 2 | [`aggressive-baseline`](bots/02-aggressive-baseline/) | `level2-verified.zip` | `LEVEL_2` | Uses the same core as iteration 1 with wider fixed opens, lower aggression thresholds, and more permissive auction choices. |
| 3 | [`open-raise-fix-conservative`](bots/03-open-raise-fix-conservative/) | `level1-practice-v2.zip` | `LEVEL_1` | Corrects unopened-pot behavior so the big blind's legal `call` option no longer causes playable hands to limp. |
| 4 | [`open-raise-fix-aggressive`](bots/04-open-raise-fix-aggressive/) | `level2-practice-v2.zip` | `LEVEL_2` | Applies the same unopened-pot fix while retaining the aggressive Level 2 thresholds. |
| 5 | [`auction-budgeting`](bots/05-auction-budgeting/) | `level1-practice-v3.zip` | `LEVEL_1` | Replaces full-tournament auction budgeting with a stack-aware survival horizon based on practice-table evidence. |
| 6 | [`wider-preflop-pressure`](bots/06-wider-preflop-pressure/) | `level3.zip` | `LEVEL_3` | Widens fixed opening ranges, carries the heads-up pressure branch forward, and scales auction budgets with pot size. |
| 7 | [`button-steal-pressure`](bots/07-button-steal-pressure/) | `level4.zip` | `LEVEL_4` | Adds a much wider button-specific opening limit while retaining Level 3 pressure and auction sizing. |
| 8 | [`equity-aware-final`](bots/08-equity-aware-final/) | `hail-mary.zip` | `HAIL_MARY` | Adds action-conditioned post-flop equity estimation, chip-EV call checks, continuation betting, and stronger value-raise gates. |

## Design highlights

- **Fast lookup-driven decisions:** precomputed class percentiles and auction shares avoid expensive enumeration on the normal action path.
- **Tournament-aware risk:** calls can be evaluated with ICM utility using the configured payout structure and stack distribution.
- **Auction resource management:** the agent scores five-card flop combinations and budgets a separate auction-chip balance over an estimated survival horizon.
- **Legal-action safety:** actions are checked and raise sizes are clamped to legal bounds, with a cheap fallback when state handling fails.
- **Selective equity calculation:** the final iteration uses exact river equity and bounded Monte Carlo estimates on flop and turn, falling back to the heuristic model on errors.

## Evaluation snapshot

The attached evaluation export covers 1,000 iterations from one of the rounds, 1,041 table records, and 148,194 hands. 

| Result | Count | Rate |
|---|---:|---:|
| First place / 50 points | 21 | 2.02% |
| Second place / 30 points | 119 | 11.43% |
| Third place / 20 points | 164 | 15.75% |
| No payout | 737 | 70.80% |
| **Any payout** | **304** | **29.20%** |
