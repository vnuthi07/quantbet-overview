"""Run the extracted pieces end to end:  python demo.py   (needs numpy and scipy)"""

from market_grid import dc_grid, fair_prob, fit_market_grid, grid_markets, total_pmf, outcome_probs
from ratings import win_prob
from sizing import compute_ev, size_bet
from value import implied_probs

# 1. De-vig a 1X2 price (made-up odds) and size a bet against a model probability
odds = {"home": 2.10, "draw": 3.40, "away": 3.60}
fair = implied_probs(odds["home"], odds["draw"], odds["away"])
print("de-vigged 1X2:", {k: round(v, 4) for k, v in fair.items()})

model_p, price = 0.52, 2.10
ev = compute_ev(model_p, price)
print(f"model 0.52 at {price}: EV {ev:+.1%} -> stake on a $100 bankroll: ${size_bet(100, model_p, price, ev):.2f}")
ev_small = compute_ev(0.48, price)
print(f"model 0.48 at {price}: EV {ev_small:+.1%} -> stake ${size_bet(100, 0.48, price, ev_small):.2f}  (under the 3% EV floor)")

# 2. Back out goal rates from a sharp book's prices, then price every other goal market off that grid.
#    Here the "sharp prices" are generated from known rates (1.60 / 1.15), so you can check the solver recovers them.
rho = -0.05
truth = dc_grid(1.60, 1.15, rho)
p1x2, p_over = outcome_probs(truth), fair_prob(total_pmf(truth), 2.5, "over")
fit = fit_market_grid(p1x2, ou_line=2.5, p_over=p_over, rho=rho)
print(f"recovered goal rates: home {fit['lam']:.3f}, away {fit['mu']:.3f}  (max fit error {fit['fit_err']:.1e})")
m = grid_markets(fit["grid"])
print("over/under ladder:", {k: round(v, 3) for k, v in m["ou"].items()})
print("both teams score:", {k: round(v, 3) for k, v in m["btts"].items()})

# 3. Glicko-2 win probability for two fighters (rating, rating deviation)
print("fighter A 1650 (RD 80) vs B 1520 (RD 120):", round(win_prob(1650, 80, 1520, 120), 3))
