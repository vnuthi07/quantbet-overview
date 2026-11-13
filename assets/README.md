# assets

Raw logs, metrics, and the charts built from them. `python ../scripts/build_charts.py` regenerates the charts and `metrics/summary.json` from these files.

| Path | What it is |
|---|---|
| `trade-logs/wc2026_trades.csv` | All 26 WC2026 knockout bets with stake, odds, result and P&L |
| `backtests/WC2018.csv`, `WC2022.csv`, `EURO2024.csv`, `COPA2024.csv` | Per-match predictions and scores from the leak-free tournament backtests |
| `metrics/summary.json` | Trade-log and backtest totals, computed from the files above |
| `metrics/mma_backtest.json` | MMA walk-forward backtest results, by year and overall |
| `charts/` | The four charts used in the README and RESULTS |

## Trade log columns

`source` says who made the call: `model`, `intuition` (my own call), or blank (no label recorded). `entry_price` and `decimal_odds` are the price I paid, `bet_size_usd` is the stake, and `pnl` is in dollars. `closing_prob` and `clv` are blank because these bets predate the rebuilt CLV measurement.

## Backtest columns

`log_loss` and `brier` are per match. The `clv` and `simulated_roi` columns compare my probability to a de-vigged odds snapshot from the morning of the match. They are not closing line value, and I don't use them for any claim (see RESULTS.md, section 2).
