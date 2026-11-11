# No-Limit Pokerbots

An archive of eight iterations of tournament pokerbot submissions built for the No-Limit Bot Building Tournament hosted by Sequoia Capital, Citadel Securities, and OpenAI. Selected as 1 of 231 teams from 6000+ global applicants for the Boston regional.

The project targets an eight-player no-limit hold'em variant with a five-card flop auction, ICM-based tournament scoring, strict per-action latency (sub-1ms), and no persistent cross-table memory. Each directory under [`bots/`](bots/) is a complete historical submission containing:

- `agent.py` — the tournament SDK entry point and selected strategy mode;
- `core.py` — betting, auction, equity, ICM, and action-safety logic;
- `policy.json` — precomputed starting-hand and auction lookup data.

## Iteration history

The folders use portfolio-friendly names. The original archive names are also here.

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

## Architecture
The agent architecture isolates decision-making into two selectable policy engines governed by an explicit build-time configuration flag (`STRATEGY_MODE`):

```
                       ┌──────────────────────────────┐
                       │    Tournament Game Engine    │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │  Legal Action Guard & Safety │
                       └──────────────┬───────────────┘
                                      │
                       ┌──────────────┴───────────────┐
                       │   STRATEGY_MODE Selector     │
                       └──────┬────────────────┬──────┘
                              │                │
            ┌─────────────────┘                └─────────────────┐
            ▼                                                    ▼
┌──────────────────────────────┐                      ┌──────────────────────────────┐
│       Level 1 Policy         │                      │       Level 2 Policy         │
│    (Mathematical Engine)     │                      │    (Exploitative Engine)     │
├──────────────────────────────┤                      ├──────────────────────────────┤
│ • Pre-computed Lookup Tables │                      │ • Per-Table Opponent Tracking│
│ • Flop Auction Value Models  │                      │ • Dynamic Exploit Thresholds │
│ • ICM & Stack Utility Models │                      │ • Targeted Steals & Pressure │
└──────────────────────────────┘                      └──────────────────────────────┘
```

## Design highlights

- **Fast lookup-driven decisions:** precomputed class percentiles and auction shares avoid expensive enumeration on the normal action path.
- **Tournament-aware risk:** calls can be evaluated with ICM utility using the configured payout structure and stack distribution.
- **Auction resource management:** the agent scores five-card flop combinations and budgets a separate auction-chip balance over an estimated survival horizon.
- **Legal-action safety:** actions are checked and raise sizes are clamped to legal bounds, with a cheap fallback when state handling fails.
- **Selective equity calculation:** the final iteration uses exact river equity and bounded Monte Carlo estimates on flop and turn, falling back to the heuristic model on errors.

## Evaluation snapshot

Observed run covering 1,000 iterations, 1,021 table records, and 144,206 hands from one of many rounds.

| Result | Count | Rate |
|---|---:|---:|
| First place / 50 points | 22 | 2.15% |
| Second place / 30 points | 148 | 14.50% |
| Third place / 20 points | 136 | 13.32% |
| No payout | 715 | 70.03% |
| **Any payout** | **306** | **29.97%** |

Mean tournament score was **8.09 points**, with a median table length of **142 hands** and **zero recorded automatic actions**. See [`performance/evaluation-summary.md`](performance/evaluation-summary.md) for methodology and additional context.
