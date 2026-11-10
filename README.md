# Sequoia No-Limit Pokerbot (`no-limit-pokerbots`)

A high-performance, modular No-Limit Texas Hold’em (NLHE) agent and evaluation framework developed for **Sequoia's No-Limit Bot Building Tournament**. 

Engineered to operate under strict production constraints (sub-millisecond decision allowances), this repository contains the agent source code, pre-computed strategy tables, local simulation tools, and test suites built specifically to navigate the tournament's unique variant rules.

---

## Tournament Overview & Game Variant

The tournament evaluates 8-player tables operating under an ICM-based tournament point system rather than pure chip expected value (Chip EV). 

* **Game Base:** Standard No-Limit Texas Hold’em rules, table settings, and payout structures.
* **The Flop Auction Twist:** In lieu of standard dealing, a **5-card auction phase** occurs for the flop, requiring agents to dynamically evaluate card value, pot odds, and resource management during the bidding and reveal phases before transitioning into post-flop execution.
* **Production Sandbox Constraints:**
  * **Strict Latency Budget:** $< 1\text{ ms}$ per-decision allowance without a standard local time bank.
  * **Memory & Persistence:** Zero cross-table memory or persistent storage; seat IDs are anonymized per table.
  * **Reliability:** Non-negotiable fault tolerance requiring robust state parsing, action clamping, and emergency check/fold fallback routines.

---

## Repository & Agent Architecture

The agent architecture isolates decision-making into two selectable policy engines governed by an explicit build-time configuration flag (`STRATEGY_MODE`):

```
                       ┌──────────────────────────────┐
                       │    Tournament Game Engine     │
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

### 1. Strategy System
* **Level 1 (Mathematical Tournament Baseline):**
  * Exact pre-computed lookup tables for pre-flop and auction states.
  * Pot odds, equity (accounting for ties/split pots), and hand-strength valuation adjusted for the 5-card flop auction dynamics.
  * ICM-aware risk utility calculated using table settings from `state.config`.
* **Level 2 (Exploitative / Loose-Aggressive Policy):**
  * In-game opponent profiling (aggression factors, fold-to-pressure ratios, showdown tendencies) limited strictly to current table history.
  * Targeted isolation raises, wider steal ranges, and value-betting gates that fall back gracefully to Level 1 logic when sample size is low.

### 2. Runtime & Safety Guardrails
* **Action Guarding:** All outputs are verified against `state.can()` or `state.legal_actions` with automatic range-clamping.
* **Emergency Fallback:** Zero-crash decision path guaranteeing a valid, cheap action (Check/Fold/Min-Raise) in the event of malformed state or latency bounds.
* **Optimized Act Path:** Low-overhead execution pipeline written to comfortably beat $p99$ tail-latency constraints under single-threaded evaluation environments.

---
### Benchmarking Decision Latency
```bash
python tests/test_latency.py --iterations 10000
```
