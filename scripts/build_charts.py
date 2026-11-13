"""Rebuild every chart and the summary metrics in assets/ from the raw logs in assets/.

    python scripts/build_charts.py

Reads:  assets/trade-logs/wc2026_trades.csv, assets/backtests/*.csv, assets/metrics/mma_backtest.json
Writes: assets/charts/*.png, assets/metrics/summary.json
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
A = ROOT / "assets"

SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
BLUE, ORANGE = "#2a78d6", "#eb6834"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "font.family": "DejaVu Sans", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
})


def _title(ax, title, sub):
    ax.text(0, 1.14, title, transform=ax.transAxes, fontsize=13, fontweight="bold", color=INK, va="bottom")
    ax.text(0, 1.06, sub, transform=ax.transAxes, fontsize=9.5, color=INK2, va="bottom")


def _save(fig, name):
    fig.savefig(A / "charts" / name, dpi=200, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- WC2026 trade log
t = pd.read_csv(A / "trade-logs" / "wc2026_trades.csv")
t["stake"] = t["bet_size_usd"].astype(float)
t["pnl"] = t["pnl"].astype(float)
t["source"] = t["source"].fillna("unlabeled")
t = t.reset_index(drop=True)
cum = t["pnl"].cumsum()

# 1. equity curve
fig, ax = plt.subplots(figsize=(9, 4.6))
x = np.arange(0, len(t) + 1)
y = np.concatenate([[0.0], cum.values])
ax.axhline(0, color=GRID, lw=1)
ax.plot(x, y, color=BLUE, lw=2, solid_joinstyle="round")
ax.scatter(x[1:], y[1:], s=26, color=BLUE, edgecolor=SURFACE, linewidth=1.5, zorder=3)
rounds = t["round"].tolist()
starts = [i for i in range(1, len(rounds)) if rounds[i] != rounds[i - 1]]   # 0-based index of 1st bet of a new round
for i in starts:
    ax.axvline(i + 0.5, color=GRID, lw=1, ls=(0, (3, 3)))
edges = [0] + starts + [len(t)]
for lo, hi in zip(edges[:-1], edges[1:]):
    ax.text((lo + 1 + hi) / 2, 1.02, rounds[lo], transform=ax.get_xaxis_transform(), ha="center",
            va="bottom", fontsize=8.5, color=MUTED)
pk, tr = int(cum.idxmax()) + 1, int(cum.idxmin()) + 1
ax.annotate(f"peak +${cum.max():.2f}", (pk, cum.max()), xytext=(0, 9), textcoords="offset points",
            ha="center", fontsize=9, color=INK2)
ax.annotate(f"low -${abs(cum.min()):.2f}", (tr, cum.min()), xytext=(0, -16), textcoords="offset points",
            ha="center", fontsize=9, color=INK2)
ax.annotate(f"+${cum.iloc[-1]:.2f}", (len(t), cum.iloc[-1]), xytext=(8, 0), textcoords="offset points",
            va="center", fontsize=10, color=INK, fontweight="bold")
ax.set_ylim(cum.min() - 2.2, cum.max() + 2.6)
ax.set_xlim(0, len(t) + 2.5)
ax.set_xlabel("bet number (chronological)")
ax.set_ylabel("cumulative P&L ($)")
ax.yaxis.grid(True, color=GRID, lw=0.6)
ax.set_axisbelow(True)
_title(ax, "WC2026 knockout bets: cumulative P&L",
       f"{len(t)} bets, ${t.stake.sum():.2f} staked, stakes ${t.stake.min():.2f} to ${t.stake.max():.2f} on a $100 bankroll")
_save(fig, "wc2026_equity_curve.png")

# 2. P&L by market
g = t.groupby("market").agg(n=("pnl", "size"), wins=("correct", "sum"), pnl=("pnl", "sum"),
                            stake=("stake", "sum")).sort_values("pnl")
fig, ax = plt.subplots(figsize=(9, 3.6))
cols = [BLUE if v >= 0 else ORANGE for v in g["pnl"]]
bars = ax.barh(g.index, g["pnl"], color=cols, height=0.55)
ax.axvline(0, color=MUTED, lw=1)
for yv, (idx, r) in enumerate(g.iterrows()):
    off = 6 if r.pnl >= 0 else -6
    ax.annotate(f"{r.pnl:+.2f}   ({int(r.wins)}W-{int(r.n - r.wins)}L)", (r.pnl, yv), xytext=(off, 0),
                textcoords="offset points", va="center", ha="left" if r.pnl >= 0 else "right",
                fontsize=9.5, color=INK)
lim = max(abs(g.pnl)) * 1.55
ax.set_xlim(-lim, lim)
ax.set_xlabel("P&L ($)")
ax.xaxis.grid(True, color=GRID, lw=0.6)
ax.set_axisbelow(True)
_title(ax, "WC2026 P&L by market", "advance = who goes through; spread / total_goals / btts = goal markets")
_save(fig, "wc2026_pnl_by_market.png")

# ---------------------------------------------------------------- football backtests
rows = []
frames = []
for name in ["WC2018", "WC2022", "EURO2024", "COPA2024"]:
    d = pd.read_csv(A / "backtests" / f"{name}.csv")
    d["tournament"] = name
    frames.append(d)
    rows.append({"tournament": name, "n": len(d), "accuracy": d["correct"].mean(),
                 "log_loss": d["log_loss"].mean(), "brier": d["brier"].mean()})
bt = pd.DataFrame(rows)
tot_n = bt.n.sum()
allm = pd.concat(frames, ignore_index=True)
extreme = allm[allm["log_loss"] >= 10]                    # a match where the model gave the real result ~0%
keep = allm[allm["log_loss"] < 10]
ex_t = keep.groupby("tournament")["log_loss"].mean()
pooled_ex = {"n": int(len(keep)), "accuracy": float(keep["correct"].mean()),
             "log_loss": float(keep["log_loss"].mean()), "brier": float(keep["brier"].mean())}
pooled = {"n": int(tot_n),
          "accuracy": float((bt.accuracy * bt.n).sum() / tot_n),
          "log_loss": float((bt.log_loss * bt.n).sum() / tot_n),
          "brier": float((bt.brier * bt.n).sum() / tot_n)}
UNIFORM_LL = float(-np.log(1 / 3))

fig, ax = plt.subplots(figsize=(9, 3.9))
ypos = np.arange(len(bt))[::-1]
ax.barh(ypos, bt["log_loss"], color=BLUE, height=0.55)
ax.axvline(UNIFORM_LL, color=MUTED, lw=1.5, ls=(0, (4, 3)))
ax.text(UNIFORM_LL + 0.02, ypos.min() - 0.62, f"guessing 1/3 each = {UNIFORM_LL:.3f}", fontsize=9, color=INK2,
        va="center")
for yv, (_, r) in zip(ypos, bt.iterrows()):
    ax.text(r.log_loss - 0.025, yv, f"{r.log_loss:.3f}", va="center", ha="right", fontsize=10,
            color="#ffffff", fontweight="bold")
    ax.text(1.62, yv, f"n={r.n}   acc {r.accuracy:.0%}", va="center", ha="left", fontsize=9.5, color=INK2)
ax.set_yticks(ypos)
ax.set_yticklabels(bt["tournament"])
ax.set_ylim(ypos.min() - 0.9, ypos.max() + 0.5)
ax.set_xlim(0, 2.0)
ax.set_xticks([0, 0.5, 1.0, 1.5])
ax.set_xlabel("1X2 log-loss (lower is better)", loc="left")
if len(extreme):
    r = extreme.iloc[0]
    who = {"home": r.home_team, "away": r.away_team}.get(r.result, "a draw")
    note = (f"{r.tournament} is {ex_t[r.tournament]:.3f} without one match, {r.home_team} v {r.away_team}: "
            f"the model gave {who} a 0% chance (loss {r.log_loss:.1f}).")
    ax.text(0, -0.22, note, transform=ax.transAxes, fontsize=9, color=INK2, va="top")
ax.xaxis.grid(True, color=GRID, lw=0.6)
ax.set_axisbelow(True)
_title(ax, "Football model: tournament backtests",
       "pre-match 1X2 probabilities, no market blend; small samples, read with care")
_save(fig, "backtest_logloss.png")

# ---------------------------------------------------------------- MMA walk-forward
m = json.load(open(A / "metrics" / "mma_backtest.json"))
by = pd.DataFrame(m["backtest"]["by_year"])
fig, ax = plt.subplots(figsize=(9, 4.4))
ax.axhline(np.log(2), color=MUTED, lw=1.2, ls=(0, (4, 3)))
ax.text(by.year.min(), np.log(2) + 0.002, f"coin flip = {np.log(2):.3f}", fontsize=9, color=INK2, va="bottom")
ax.plot(by.year, by.glicko, color=ORANGE, lw=2)
ax.plot(by.year, by.model, color=BLUE, lw=2)
ax.scatter(by.year, by.glicko, s=22, color=ORANGE, edgecolor=SURFACE, linewidth=1.2, zorder=3)
ax.scatter(by.year, by.model, s=22, color=BLUE, edgecolor=SURFACE, linewidth=1.2, zorder=3)
last = by.iloc[-1]
ax.annotate("full model", (last.year, last.model), xytext=(8, 0), textcoords="offset points", va="center",
            fontsize=10, color=INK, fontweight="bold")
ax.annotate("Glicko-2 only", (last.year, last.glicko), xytext=(8, 0), textcoords="offset points", va="center",
            fontsize=10, color=INK)
ax.set_xlim(by.year.min() - 0.3, by.year.max() + 2.6)
ax.set_xticks(list(range(int(by.year.min()), int(by.year.max()) + 1, 2)))
ax.set_ylabel("log-loss per fight (lower is better)")
ax.yaxis.grid(True, color=GRID, lw=0.6)
ax.set_axisbelow(True)
bt_m = m["backtest"]
_title(ax, "MMA win model: walk-forward log-loss by year",
       f"{bt_m['n']:,} fights, refit every {bt_m['refit_days']} days, each fight predicted from earlier fights only")
_save(fig, "mma_walkforward_by_year.png")

# ---------------------------------------------------------------- summary.json
by_src = t.groupby("source").agg(n=("pnl", "size"), wins=("correct", "sum"), pnl=("pnl", "sum"),
                                 stake=("stake", "sum")).round(2)
by_round = t.groupby("round", sort=False).agg(n=("pnl", "size"), wins=("correct", "sum"), pnl=("pnl", "sum"),
                                              stake=("stake", "sum")).round(2)
summary = {
    "wc2026_trades": {
        "n": int(len(t)), "wins": int(t.correct.sum()), "losses": int((~t.correct).sum()),
        "staked": round(float(t.stake.sum()), 2), "pnl": round(float(t.pnl.sum()), 2),
        "roi_on_staked": round(float(t.pnl.sum() / t.stake.sum()), 4),
        "peak_cum_pnl": round(float(cum.max()), 2), "low_cum_pnl": round(float(cum.min()), 2),
        "max_drawdown_usd": round(float((cum.cummax() - cum).max()), 2),
        "by_market": g.round(2).reset_index().to_dict("records"),
        "by_source_label": by_src.reset_index().to_dict("records"),
        "by_round": by_round.reset_index().to_dict("records"),
    },
    "football_backtests": {"uniform_log_loss": round(UNIFORM_LL, 4),
                           "per_tournament": bt.round(4).to_dict("records"),
                           "pooled": {k: round(v, 4) for k, v in pooled.items()},
                           "zero_probability_matches": extreme[["date", "tournament", "home_team", "away_team", "result", "log_loss"]]
                                          .to_dict("records"),
                           "pooled_without_those_matches": {k: round(v, 4) for k, v in pooled_ex.items()},
                           "per_tournament_without_those_matches": {k: round(float(v), 4) for k, v in ex_t.items()}},
    "mma_walkforward": {"years": int(len(by)), "years_model_beats_glicko": int((by.model < by.glicko).sum()),
                        "years_model_worse": by.loc[by.model >= by.glicko, "year"].tolist()},
}
(A / "metrics" / "summary.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary["wc2026_trades"], indent=1)[:900])
print(summary["football_backtests"])
