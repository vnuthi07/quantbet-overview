"""Stake sizing and closing-line value, extracted from betting/clv.py.

Rules in force: no bet below 3% EV, tiered fractional Kelly (never full Kelly),
hard 3% of bankroll cap per bet.
"""

from __future__ import annotations

from value import expected_value, kelly_fraction


def compute_ev(prob: float, decimal_odds: float) -> float:
    """Expected value per $1 staked at the given decimal odds."""
    return expected_value(prob, decimal_odds)


def fractional_kelly(prob: float, decimal_odds: float, fraction: float = 0.25) -> float:
    """Fractional Kelly stake fraction (never full Kelly)."""
    return kelly_fraction(prob, decimal_odds) * fraction


def compute_clv(your_prob: float, closing_prob: float) -> float:
    """Closing Line Value: how much your probability beat the closing line.
    Positive over a large sample = a genuine edge."""
    return (your_prob / closing_prob - 1.0) if closing_prob and closing_prob > 0 else 0.0


def size_bet(bankroll: float, prob: float, decimal_odds: float, ev: float,
             *, max_fraction: float = 0.03) -> float:
    """Tiered fractional Kelly with a hard per-bet cap. No bet below 3% EV."""
    if ev < 0.03:
        return 0.0
    fraction = 0.25 if ev < 0.07 else (0.33 if ev < 0.12 else 0.50)
    stake = fractional_kelly(prob, decimal_odds, fraction) * bankroll
    return round(min(stake, bankroll * max_fraction), 2)
