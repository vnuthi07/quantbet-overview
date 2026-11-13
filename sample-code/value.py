"""Betting value: compare model probabilities to bookmaker odds.

Steps: strip the bookmaker margin from decimal odds to get their implied "fair"
probabilities, compute expected value per outcome against the model's probability,
flag positive-edge bets, and size them with fractional Kelly against a bankroll.
"""

from __future__ import annotations

_CLASSES = ("home", "draw", "away")


def implied_probs(odds_home: float, odds_draw: float, odds_away: float) -> dict[str, float]:
    """De-vig: normalise 1/odds so the implied probabilities sum to 1."""
    raw = {"home": 1.0 / odds_home, "draw": 1.0 / odds_draw, "away": 1.0 / odds_away}
    overround = sum(raw.values())
    return {c: raw[c] / overround for c in _CLASSES}


def expected_value(prob: float, decimal_odds: float) -> float:
    """EV per 1 unit staked: prob * (odds - 1) - (1 - prob)."""
    return prob * (decimal_odds - 1.0) - (1.0 - prob)


def kelly_fraction(prob: float, decimal_odds: float) -> float:
    """Full-Kelly stake fraction; 0 when there's no edge."""
    b = decimal_odds - 1.0
    if b <= 0:
        return 0.0
    f = (prob * b - (1.0 - prob)) / b
    return max(0.0, f)


def find_value(
    model_probs: dict[str, float],
    odds: dict[str, float],
    *,
    bankroll: float,
    kelly_frac: float = 0.25,
    min_edge: float = 0.03,
) -> list[dict]:
    """Return value bets (EV edge above min_edge), with recommended stakes.

    `odds` keys: odds_home, odds_draw, odds_away (decimal).
    """
    odds_map = {"home": odds.get("odds_home"), "draw": odds.get("odds_draw"), "away": odds.get("odds_away")}
    book_fair = implied_probs(odds_map["home"], odds_map["draw"], odds_map["away"])
    bets = []
    for c in _CLASSES:
        o = odds_map[c]
        if not o:
            continue
        ev = expected_value(model_probs[c], o)
        edge = model_probs[c] - book_fair[c]
        if ev > min_edge:
            stake = kelly_frac * kelly_fraction(model_probs[c], o) * bankroll
            bets.append({
                "selection": c,
                "decimal_odds": round(o, 3),
                "model_prob": round(model_probs[c], 4),
                "book_fair_prob": round(book_fair[c], 4),
                "edge": round(edge, 4),
                "ev_per_unit": round(ev, 4),
                "stake": round(stake, 2),
            })
    bets.sort(key=lambda d: d["ev_per_unit"], reverse=True)
    return bets
