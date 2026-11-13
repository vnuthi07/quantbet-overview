# Methodology

How the system works and the rules it runs on. Numbers here are the settings in use as of Nov 13, 2026.

## 1. What I'm trying to find

I'm not trying to predict winners. I'm trying to find contracts that are priced worse than they should be. A heavy favorite can be the correct pick and still a bad bet at the price.

The only edge I think is realistic is **line-shopping**: Pinnacle is the sharpest price available, and Kalshi and Polymarket are often softer. When one of them sells a contract for less than Pinnacle's fair price, after fees, that is a signal. A model that just copies the market has no edge, so my own model stays as a shadow reference and is not what I bet on.

I judge everything by expected value and closing line value (CLV), not by win rate. Win rate over a few dozen bets is noise.

## 2. Data

| Source | Used for |
|---|---|
| The Odds API (Pinnacle, h2h and totals) | The sharp reference price |
| Kalshi | Contract prices and order book depth |
| Polymarket | Contract prices and order book depth |
| football-data.co.uk | Historical results and closing odds for EPL calibration |
| UFC Stats (public mirror of the scraped data) | Fight history for the MMA model |

The Odds API is metered by credits, so calls are budgeted: every 10 minutes within 3 hours of kickoff, plus calls at 5 minutes and 1 minute before, hourly on match days, and every 2 hours as a baseline within 72 hours. Kalshi and Polymarket are polled every 60 seconds.

## 3. Fair price

Bookmaker odds include a margin. I remove it by normalizing implied probabilities so they sum to 1 (`sample-code/value.py`). That de-vigged Pinnacle probability is the fair price.

A signal is only **anchored** if the Pinnacle price is fresh (under 15 minutes old) and matches the same fixture and market. Everything else is paper-only and stakes nothing.

## 4. Fees and the gap

The all-in price is the best ask plus the fee. I model fees per contract as:

- Kalshi: about 0.07 x p x (1 - p)
- Polymarket (taker): about 0.05 x p x (1 - p)

**Gap = Pinnacle probability - (best ask + fee).** A positive gap means the contract is cheaper than Pinnacle's fair price after fees.

## 5. Signal tiers

Every signal gets a tier from its expected value, and some tiers can never stake.

| Tier | Rule | Stake |
|---|---|---|
| skip | EV under 3% | 0 |
| borderline | EV 3-5% | small |
| actionable | EV 5-20% | sized below |
| artifact | EV over 20% | 0 |
| thin | price outside 0.10-0.90 (illiquid) | 0 |
| paper | not anchored to a fresh sharp price | 0 |
| derived | priced from the market-implied grid, not a quoted market | 0 |
| live | in-play | no signals |

The artifact rule exists because a huge edge almost always means a data error or an illiquid market. In my own tournament backtests the model "disagreed" with the market by more than 80% on average, which is the same warning.

## 6. Sizing

Tiered fractional Kelly with a hard cap (`sample-code/sizing.py`):

- No bet below 3% EV.
- Kelly fraction is 0.25 below 7% EV, 0.33 from 7-12%, 0.50 above 12%. Never full Kelly.
- Hard cap of 3% of bankroll per bet.
- Correlated bets (for example several markets on the same match) are cluster-capped instead of treated as independent, and total exposure is capped at 40% of bankroll.

## 7. Market-implied score grid

Pinnacle quotes 1X2 and one main totals line. I solve for the home and away goal rates so a Dixon-Coles score grid reproduces those prices, holding the league's fitted correlation term (rho) fixed. That grid then prices every other goal market consistently: over/under at every line, both teams to score, clean sheets (`sample-code/market_grid.py`).

Asian totals lines are handled exactly. A whole line (3.0) pushes on a tie, and a quarter line (2.75) splits the stake between its two neighbours. On Pinnacle's own alternate 2.5 line the grid matched within an average of 0.29 percentage points.

## 8. Models

**Football (shadow reference).** A Dixon-Coles bivariate Poisson goal model with time decay, a LightGBM win/draw/loss classifier on Elo, form and goal-trend features, blended with a weight learned on a validation window, then isotonic-calibrated. Rating add-ons (pi-ratings, a Kalman-filtered strength) added almost nothing on top of Elo, so they are not a lever.

**MMA.**
- Glicko-2 ratings for every fighter, updated one rating period per event from pre-event values so nothing on a card leaks into another fight on the same card.
- Two MMA adjustments: rating uncertainty grows with inactivity, and a fighter who changes weight class gets extra uncertainty. Debutants start at rating 1500 with uncertainty 250.
- A logistic regression on pre-fight differences (18 features): Glicko rating, rating uncertainty, reach, height, age, layoff, striking volume and accuracy, takedown offence and defence, submission and knockdown rates, control time share, finish rate, KO-loss rate, win streak and experience.
- A separate multinomial model for method of victory (KO/TKO, submission, decision).
- Validated walk-forward: refit every 90 days, and every fight is predicted using only earlier fights.

## 9. Measurement

- **Snapshots.** Every poll is logged. The cadence is adaptive: once a minute when the gap is 1 point or more or the fixture is within 3 hours, every 10 minutes otherwise.
- **Closing line.** The last fresh snapshot before kickoff.
- **Executable only if the book can fill it.** A signal counts only when the order book size covers the stake (a nominal $5 when the real stake is 0).
- **CLV.** My probability against the closing probability. Rows flagged as correlated are excluded.

## 10. Rules I set before collecting data

These were fixed in config before the live data existed, so I can't move the goalposts later.

**Verdict (`leagues verdict`)** returns CONTINUE, STOP or INSUFFICIENT DATA. It needs at least 30 fixtures across at least 3 rounds (for MMA, 40 fights across 4 events), a gap of at least 1.5 points sustained for at least 3 minutes (four consecutive fresh 1-minute snapshots), and at least 10% of observations qualifying. Until the sample is big enough it withholds the share instead of printing a number that looks meaningful.

**Graduation gate.** Real stakes only after at least 150 settled actionable signals with a closing line, and the lower bound of a bootstrap 95% confidence interval on mean CLV is above zero. Paper signals don't count toward it.

## 11. Architecture

- `leagues watch` is the single producer. It polls, writes snapshots and the ledger, and atomically writes `latest_board.json`.
- A read-only FastAPI service serves that file. No route calls The Odds API or places an order, and it binds to localhost.
- A Next.js dashboard consumes the API.
- All writes go through one module with atomic writes, locks and retries, and each poll has a 90-second watchdog.

## 12. Known limits

- The football model has not beaten the market. The 26 real bets don't change that.
- Tournament backtests are small (32-64 matches each). In WC2022 the model gave Cameroon a 0% chance of beating Brazil, and that one match dominates the tournament's score. A model that can output an exact zero is a flaw.
- MMA has not been compared to market odds yet. I still need a historical closing-odds file.
- Gap data is thin so far. It needs real match days to accumulate.
- Fee formulas are approximations of each platform's schedule.
