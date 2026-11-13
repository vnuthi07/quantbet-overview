# Changelog

## 2026-11-13
- Published this overview repo: methodology, results, logs, charts, and runnable sample code. The working engine stays private.

## 2026-11
League engine, dashboard and MMA, built over a few days starting Nov 11.

- Generalized the World Cup tool into a league-agnostic engine that fetches live Kalshi, Polymarket and Odds API prices for whatever leagues are in season. First league: Premier League.
- Added signal tiers (skip, borderline, actionable, artifact, thin, paper, derived, live) so unanchored and illiquid prices can never stake.
- Added the market-implied score grid, which prices over/under at every line, BTTS and clean sheets off Pinnacle's 1X2 and main totals.
- Added snapshot logging with a 15-minute staleness limit, adaptive polling, a closing line taken from the last fresh snapshot, and order-book depth.
- Added the pre-set verdict rule (CONTINUE, STOP, INSUFFICIENT DATA) and the graduation gate: 150 settled signals and a bootstrap CI on CLV above zero.
- Hardened the watcher: atomic writes, file locks, retries, and a 90-second watchdog per poll.
- Replaced the Streamlit dashboard with FastAPI (read-only, localhost) and Next.js.
- Built the MMA module: Glicko-2 ratings with inactivity and weight-change uncertainty, a logistic win model on 18 pre-fight features, a method-of-victory model, and a walk-forward backtest over 5,497 fights.
- Began live paper trading for the Premier League and MMA.
- Fixed a gap-backfill bug where quiet candlestick periods were treated as no ask, and a Kalshi parser that rejected every EPL market.
- Test suite grew to 279 tests.

## 2026-07
World Cup 2026 knockout trading.

- Placed 26 real bets from the Round of 32 to the semi-final (13W-13L, +$4.04 on $64.48 staked).
- Added the Kelly sizing and result-logging commands, and a rule that discretionary bets stay out of the performance log.
- Found that my CLV logger treated the entry price as the closing price, so it always read zero. Flagged it, then rebuilt the measurement in November.
- Ran leak-free backtests on WC2018, WC2022, Euro 2024 and Copa America 2024.
- Restricted bets to advance and full-game totals while travelling, and added cluster caps after noticing stacked Under bets on one match were being treated as independent.

## 2026-06 and earlier
- First World Cup model: Dixon-Coles goal model, LightGBM classifier with isotonic calibration, a Monte Carlo tournament simulation, and a market blend toward a Pinnacle anchor.
