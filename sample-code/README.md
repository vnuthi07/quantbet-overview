# sample-code

Small pieces of the engine, pulled out so they run on their own. The full engine is private.

| File | What it does |
|---|---|
| `value.py` | De-vig bookmaker odds, EV per unit, full Kelly fraction |
| `sizing.py` | Tiered fractional Kelly with a 3% per-bet cap and a 3% EV floor, plus the CLV formula |
| `market_grid.py` | Backs out the goal rates a sharp book is pricing, rebuilds a Dixon-Coles score grid from them, and prices over/under at every line (Asian quarter lines included), BTTS and clean sheets |
| `ratings.py` | Glicko-2 for fighters, with an inactivity term and extra uncertainty when a fighter changes weight class |
| `demo.py` | Runs all of the above |

```bash
pip install numpy scipy
python demo.py
```

`value.py` and `ratings.py` are copied unchanged. `sizing.py` is the sizing and CLV
functions from `betting/clv.py` without the logging code. `market_grid.py` is
`leagues/derived.py` with two small helpers inlined so it doesn't import the rest of the repo.
