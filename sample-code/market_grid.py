"""Market-implied Dixon-Coles grid: back out (lambda, mu) from Pinnacle's prices.

Given Pinnacle's de-vigged 1X2 and its de-vigged price on the MAIN totals line, solve for
the home/away goal rates (lambda, mu) — holding the league model's fitted rho — such that
the Dixon-Coles score grid reproduces those prices (least squares on four residuals:
P(home), P(draw), P(away), fair P(over L)). The grid then prices every other goal market
(O/U at every line, BTTS, clean sheets) consistently with the sharp book.

Asian totals lines (Pinnacle's main line is often 2.75 / 3.0 / 3.25):

  * X.5            over wins if T > X.5, loses otherwise
  * X.0  (whole)   over wins if T > X, PUSH (stake back) if T == X, loses if T < X
  * X.25 / X.75    split stake: half on each neighbouring line (2.75 = 2.5 + 3.0)

The "fair over probability" on such a line is the p for which decimal odds 1/p have zero
EV. Summing over the split components c with weight w:

      EV_over(O) = sum_c w * [P(T > c) * (O - 1) - P(T < c)]   = 0
  =>  p_over     = sum w*P(T>c) / (sum w*P(T>c) + sum w*P(T<c))

which is exactly what a proportional two-way de-vig of the over/under prices estimates.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import least_squares
from scipy.stats import poisson


X5_LINES = (0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5)


# --- two small helpers that live in models/derived.py in the full repo, inlined so this file runs alone ---

def outcome_probs(grid: np.ndarray) -> dict:
    """P(home win), P(draw), P(away win) from a score grid indexed [home_goals, away_goals]."""
    return {"home": float(np.tril(grid, -1).sum()), "draw": float(np.trace(grid)),
            "away": float(np.triu(grid, 1).sum())}


def both_teams_to_score(grid: np.ndarray) -> dict:
    yes = float(grid[1:, 1:].sum())
    return {"yes": yes, "no": 1.0 - yes}


def dc_grid(lam: float, mu: float, rho: float, max_goals: int = 10) -> np.ndarray:
    """Dixon-Coles score grid (same construction as models.dixon_coles.score_matrix)."""
    k = np.arange(max_goals + 1)
    grid = np.outer(poisson.pmf(k, lam), poisson.pmf(k, mu))
    grid[0, 0] *= 1 - lam * mu * rho
    grid[0, 1] *= 1 + lam * rho
    grid[1, 0] *= 1 + mu * rho
    grid[1, 1] *= 1 - rho
    grid = np.clip(grid, 1e-15, None)
    return grid / grid.sum()


def total_pmf(grid: np.ndarray) -> np.ndarray:
    """P(total goals == t) for t = 0..2*max_goals."""
    n = grid.shape[0]
    pmf = np.zeros(2 * n - 1)
    for i in range(n):
        pmf[i:i + n] += grid[i]
    return pmf


def asian_components(line: float) -> list[tuple[float, float]]:
    """2.75 -> [(2.5, .5), (3.0, .5)];  3.0 -> [(3.0, 1)];  2.5 -> [(2.5, 1)]."""
    q = round(line * 4)
    if q % 2 == 1:                                    # quarter line
        return [(line - 0.25, 0.5), (line + 0.25, 0.5)]
    return [(line, 1.0)]


def _win_push_lose(pmf: np.ndarray, c: float, side: str) -> tuple[float, float, float]:
    t = np.arange(len(pmf))
    over, push, under = float(pmf[t > c].sum()), float(pmf[np.isclose(t, c)].sum()), float(pmf[t < c].sum())
    return (over, push, under) if side == "over" else (under, push, over)


def asian_ev(pmf: np.ndarray, line: float, odds: float, side: str = "over") -> float:
    """EV per 1 unit staked at decimal `odds` on `side` of an (Asian) totals line."""
    ev = 0.0
    for c, w in asian_components(line):
        win, _push, lose = _win_push_lose(pmf, c, side)
        ev += w * (win * (odds - 1.0) - lose)
    return ev


def fair_prob(pmf: np.ndarray, line: float, side: str = "over") -> float:
    """Probability p whose decimal price 1/p is zero-EV on this (Asian) line."""
    W = L = 0.0
    for c, w in asian_components(line):
        win, _push, lose = _win_push_lose(pmf, c, side)
        W += w * win
        L += w * lose
    return W / (W + L) if (W + L) > 0 else float("nan")


def fit_market_grid(p1x2: dict, ou_line: float, p_over: float, rho: float, *, max_goals: int = 10,
                    x0: tuple[float, float] = (1.45, 1.15)) -> dict:
    """Least-squares (lambda, mu) reproducing de-vigged 1X2 + fair P(over ou_line).

    Returns {lam, mu, rho, grid, fit_err (max abs residual), resid, success}."""
    target = np.array([p1x2["home"], p1x2["draw"], p1x2["away"], p_over], dtype=float)

    def resid(x):
        lam, mu = math.exp(x[0]), math.exp(x[1])
        g = dc_grid(lam, mu, rho, max_goals)
        o = outcome_probs(g)
        return np.array([o["home"], o["draw"], o["away"], fair_prob(total_pmf(g), ou_line, "over")]) - target

    # a cheap start from the 1X2 skew helps the solver on lopsided matches
    skew = math.log(max(p1x2["home"], 1e-3) / max(p1x2["away"], 1e-3))
    start = np.log([max(x0[0] * math.exp(0.35 * skew), 0.05), max(x0[1] * math.exp(-0.35 * skew), 0.05)])
    sol = least_squares(resid, start, method="lm", xtol=1e-15, ftol=1e-15, gtol=1e-15, max_nfev=2000)
    lam, mu = math.exp(sol.x[0]), math.exp(sol.x[1])
    g = dc_grid(lam, mu, rho, max_goals)
    r = resid(sol.x)
    return {"lam": lam, "mu": mu, "rho": rho, "grid": g, "resid": r.tolist(),
            "fit_err": float(np.abs(r).max()), "success": bool(sol.success)}


def grid_markets(grid: np.ndarray) -> dict:
    """Every goal market the board prices from a grid."""
    pmf = total_pmf(grid)
    return {"1x2": outcome_probs(grid),
            "ou": {ln: fair_prob(pmf, ln, "over") for ln in X5_LINES},
            "btts": both_teams_to_score(grid),
            "cs": {"home": float(grid[:, 0].sum()), "away": float(grid[0, :].sum())}}
