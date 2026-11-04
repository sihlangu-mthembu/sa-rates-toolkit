# sa-rates-toolkit

A small Python toolkit covering the core mechanics of South African interest-rate markets: it builds a **zero curve** from government bond par yields, values a **bond portfolio** and its **DV01**, sizes a **ZARONIA interest rate swap** to hedge that portfolio, and shows what the hedge does and doesn't protect against under parallel moves and curve twists.

**All market inputs are illustrative**: round numbers in the general range of South African government bond yields in 2025–26, not live market data.

## Quick start

Needs Python 3.10 or newer. No packages to install.

```bash
python run.py                      # writes reports/report.md and reports/curve.svg
python -m unittest discover tests  # run the tests
```

## What it does

1. **Bootstraps a zero curve.** Starting from 1- to 10-year par yields, it solves for the discount factor at each tenor so that every par bond reprices to exactly 100. The tests check that property.
2. **Values a bond portfolio.** For R200 million face value across 3-, 7- and 10-year bonds, it calculates each bond's price, modified duration and **DV01**, the rand change in value for a 0.01% (1 basis point) move in rates. Portfolio DV01 is about **−R94,600**: a 1bp rise in rates costs the portfolio about R94,600.
3. **Sizes a swap hedge.** A 7-year **payer swap** (pay fixed, receive compounded ZARONIA) gains when rates rise, so it offsets the bonds. The notional is chosen so the swap's DV01 cancels the portfolio's: about **R191 million**.
4. **Runs scenarios:**

| Scenario | Bonds | Swap hedge | Net |
| --- | --- | --- | --- |
| Parallel +100bp | −R9.14m | +R9.16m | +R0.02m |
| Parallel −100bp | +R9.81m | −R9.79m | +R0.02m |
| Bear steepener (10y +100bp) | −R5.85m | +R5.41m | −R0.44m |
| Twist (1y +50bp, 10y −50bp) | +R1.36m | −R0.81m | +R0.55m |

## What the results teach

- **DV01 hedging works for parallel moves:** a R9 million swing is cut to about R20,000.
- **What's left in parallel moves is convexity.** Bond prices change non-linearly, so for big moves the portfolio gains a little more than DV01 predicts when rates fall and loses a little less when they rise. That's why the net result is slightly positive both ways.
- **Curve changes are not hedged.** The bonds' risk sits at 3, 7 and 10 years, but the hedge sits at 7. When the curve steepens or twists, the residual is R400,000–550,000. This is **curve risk**, and the fix is to split the hedge across several tenors (key-rate hedging).

## Why ZARONIA, not JIBAR

JIBAR, South Africa's traditional floating reference rate, will be published for the last time on **31 December 2026**, and **ZARONIA** is its successor. The swap here therefore references compounded ZARONIA, modelled as an overnight-indexed swap.

## Simplifications

These are deliberate, and stated so they can be discussed:

- **Annual payments.** Coupons and swap payments are annual; South African government bonds actually pay semi-annually.
- **One curve.** The same curve is used for discounting and forecasting. Real desks build separate curves (and the bond curve and swap curve differ).
- **Basic curve maths.** Zero rates are linearly interpolated with annual compounding, and there are no day-count conventions or settlement lags.
- **Illustrative data.** Inputs are not live market prices.

## Project structure

```
sa-rates-toolkit/
├── rates.py          # bootstrap, discount factors, bond and swap pricing, DV01, duration
├── run.py            # portfolio, hedge sizing, scenarios, report and chart
├── reports/          # report.md, curve.svg
└── tests/test_rates.py
```

## Author

Sihlangu Mthembu, Economics & Politics, University of Cape Town. Built to deepen the fixed-income exposure from my internship at Ashburton Investments.
