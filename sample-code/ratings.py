"""Glicko-2 (Glickman 2012) for fighters, with two MMA adjustments.

* Inactivity: before a fight, phi grows by sigma^2 per elapsed rating period
  (period_days, default 30): phi* = sqrt(phi^2 + t * sigma^2), capped at the initial phi.
* Weight-class awareness: a fighter appearing at a different weight (lbs) than in their
  previous fight gets extra uncertainty, phi = sqrt(phi^2 + (weight_change_phi/173.7)^2):
  a lightweight moving to welterweight is a less certain proposition than the rating says.
* Debutants start at mu=1500 with phi=debut_phi (250: UFC signings are pre-screened, so the
  textbook 350 is too wide).

Each event is one rating period for the fighters on it, updated simultaneously from their
PRE-event values, so nothing on a card leaks into another fight on the same card.
"""

from __future__ import annotations

import math

SCALE = 173.7178


def g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / (math.pi ** 2))


def expected(mu: float, mu_j: float, phi_j: float) -> float:
    return 1.0 / (1.0 + math.exp(-g(phi_j) * (mu - mu_j)))


def win_prob(r_a: float, rd_a: float, r_b: float, rd_b: float) -> float:
    """P(A beats B) from ratings on the Glicko scale (both uncertainties combined)."""
    mu_a, mu_b = (r_a - 1500) / SCALE, (r_b - 1500) / SCALE
    phi = math.sqrt((rd_a / SCALE) ** 2 + (rd_b / SCALE) ** 2)
    return 1.0 / (1.0 + math.exp(-g(phi) * (mu_a - mu_b)))


def _new_sigma(sigma: float, phi: float, v: float, delta: float, tau: float, eps: float = 1e-6) -> float:
    a = math.log(sigma * sigma)

    def f(x):
        ex = math.exp(x)
        return ex * (delta * delta - phi * phi - v - ex) / (2 * (phi * phi + v + ex) ** 2) - (x - a) / (tau * tau)

    A = a
    if delta * delta > phi * phi + v:
        B = math.log(delta * delta - phi * phi - v)
    else:
        k = 1
        while f(a - k * tau) < 0:
            k += 1
        B = a - k * tau
    fa, fb = f(A), f(B)
    for _ in range(100):
        if abs(B - A) <= eps:
            break
        C = A + (A - B) * fa / (fb - fa)
        fc = f(C)
        if fc * fb <= 0:
            A, fa = B, fb
        else:
            fa = fa / 2
        B, fb = C, fc
    return math.exp(A / 2)


def update_period(r: float, rd: float, sigma: float, games, tau: float) -> tuple[float, float, float]:
    """Glicko-2 rating-period update (Glickman 2012, steps 2-8) on the rating scale.
    games = [(r_opp, rd_opp, score)], score 1 win / 0.5 draw / 0 loss."""
    mu, phi = (r - 1500) / SCALE, rd / SCALE
    if not games:
        return r, SCALE * math.sqrt(phi * phi + sigma * sigma), sigma
    inv_v, dsum = 0.0, 0.0
    for r_opp, rd_opp, score in games:
        mu_j, phi_j = (r_opp - 1500) / SCALE, rd_opp / SCALE
        gj = g(phi_j)
        E = expected(mu, mu_j, phi_j)
        inv_v += gj * gj * E * (1 - E)
        dsum += gj * (score - E)
    v = 1.0 / inv_v
    delta = v * dsum
    sig = _new_sigma(sigma, phi, v, delta, tau)
    phi_star = math.sqrt(phi * phi + sig * sig)
    phi_new = 1.0 / math.sqrt(1.0 / (phi_star ** 2) + 1.0 / v)
    mu_new = mu + phi_new * phi_new * dsum
    return 1500 + SCALE * mu_new, SCALE * phi_new, sig


def update(r: float, rd: float, sigma: float, r_opp: float, rd_opp: float, score: float, tau: float
           ) -> tuple[float, float, float]:
    """One-fight Glicko-2 update (a fighter has one bout per event = one rating period)."""
    return update_period(r, rd, sigma, [(r_opp, rd_opp, score)], tau)


def inflate(rd: float, sigma: float, days: float | None, *, period_days: float, max_rd: float) -> float:
    """Inactivity: phi grows by sigma^2 per elapsed period (capped at max_rd)."""
    if days is None or days <= 0:
        return rd
    phi = rd / SCALE
    t = days / period_days
    return min(SCALE * math.sqrt(phi * phi + t * sigma * sigma), max_rd)


def weight_change(rd: float, extra_rd: float, max_rd: float) -> float:
    return min(math.sqrt(rd * rd + extra_rd * extra_rd), max_rd)
