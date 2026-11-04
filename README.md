# sa-rates-toolkit

A Python toolkit (pandas, NumPy, SciPy) covering the core mechanics of interest-rate markets, built around South Africa with a US module:

- **ZAR zero curve:** bootstrapped from government bond par yields, then fitted with a **Nelson-Siegel** model (SciPy least squares).
- **Bond portfolio risk:** prices, **yields to maturity** (SciPy root finding), modified duration and **DV01**.
- **Carry and roll-down:** what each bond earns over a year if the curve doesn't move.
- **ZARONIA swap hedge:** sizes an interest rate swap to offset the portfolio's DV01 and tests it under parallel moves, steepeners, flatteners and twists.
- **US module:** an illustrative **SOFR** swap curve, and **Treasury futures** cheapest-to-deliver analysis using conversion factors and gross basis.

**All market inputs are illustrative**: round numbers in plausible ranges, not live market data.

## Quick start

```bash
pip install -r requirements.txt    # pandas, numpy, scipy
python run.py                      # writes reports/report.md and reports/curve.svg
python -m unittest discover tests  # 8 tests
```

## Key results

**Portfolio and hedge:**
- **The portfolio:** R200m face across 3-, 7- and 10-year bonds, with a DV01 of about **−R94,600 per basis point**.
- **The hedge:** a **R191m 7-year ZARONIA payer swap** offsets that DV01.

| Scenario | Bonds | Swap hedge | Net |
| --- | --- | --- | --- |
| Parallel +100bp | −R9.14m | +R9.16m | +R0.02m |
| Parallel −100bp | +R9.81m | −R9.79m | +R0.02m |
| Bear steepener (10y +100bp) | −R5.85m | +R5.41m | −R0.44m |
| Bull flattener (10y −100bp) | +R6.26m | −R5.66m | +R0.60m |
| Twist (1y +50bp, 10y −50bp) | +R1.36m | −R0.81m | +R0.55m |

- **Parallel moves are hedged.** The small positive residual both ways is convexity.
- **Curve-shape moves are not.** The bonds' risk sits at 3, 7 and 10 years while the hedge sits at 7, so steepeners and twists leave R0.4–0.6m of curve risk. The fix is key-rate hedging across several tenors.

**Carry and roll-down (1 year, curve unchanged):**

| Bond | Carry | Roll-down | Total |
| --- | --- | --- | --- |
| 3-year | 0.52% | 0.62% | 1.14% |
| 7-year | 1.64% | 1.55% | 3.19% |
| 10-year | 2.44% | 1.15% | 3.59% |

Carry is coupon income minus the cost of funding at the 1-year rate. Roll-down is the price gain as the bond ages into a shorter, lower-yielding part of an upward-sloping curve. Roll-down peaks at 7 years, where this curve is steepest.

**Nelson-Siegel:** level, slope and curvature summarise the 10-point curve within 1.9bp RMSE.

**Treasury futures:** of four illustrative deliverable notes, the 4.000% 2032 has the lowest gross basis (cash price minus futures price × conversion factor), so it is cheapest to deliver.

## Why ZARONIA, not JIBAR

JIBAR, South Africa's traditional floating reference rate, publishes for the last time on **31 December 2026**, and **ZARONIA** is its successor, just as SOFR replaced USD LIBOR. The swaps here reference compounded overnight rates.

## Simplifications

These are deliberate, and stated so they can be discussed:

- **Annual payments.** ZAR coupons and swap payments are annual; South African government bonds actually pay semi-annually.
- **Basic curve maths.** One curve is used for discounting and forecasting, zero rates are linearly interpolated, and there are no day-count conventions.
- **Simplified Treasury futures.** The conversion factor is approximate, with no accrued interest, implied repo or delivery options.
- **Illustrative data.** No transaction costs, and inputs are not live market prices.

## Project structure

```
sa-rates-toolkit/
├── rates.py        # NumPy: bootstrap, discounting, bond and swap pricing, DV01, duration
├── analytics.py    # SciPy/pandas: Nelson-Siegel fit, yield to maturity, carry and roll-down
├── us_markets.py   # SOFR swap curve, Treasury futures conversion factors and cheapest-to-deliver
├── run.py          # builds the portfolio, hedge, scenarios and report (pandas tables)
├── reports/        # report.md, curve.svg
└── tests/test_rates.py
```

## Author

Sihlangu Mthembu, Economics & Politics (UCT); Fixed Income and Quantitative Methods for Investment (Milpark, NQF 8). Built to deepen the fixed income exposure from my internship at Ashburton Investments.
