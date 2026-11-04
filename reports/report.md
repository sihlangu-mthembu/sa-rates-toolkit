# SA rates toolkit report

Generated 2026-11-04 21:17. **All market inputs are illustrative, not live data.**

## 1. Zero curve

Bootstrapped from annual par yields. ![curve](curve.svg)

| Tenor | Par yield | Zero rate | Discount factor |
| --- | --- | --- | --- |
| 1y | 7.50% | 7.500% | 0.9302 |
| 2y | 7.80% | 7.812% | 0.8603 |
| 3y | 8.10% | 8.133% | 0.7909 |
| 4y | 8.40% | 8.466% | 0.7225 |
| 5y | 8.70% | 8.813% | 0.6555 |
| 6y | 9.00% | 9.177% | 0.5905 |
| 7y | 9.30% | 9.560% | 0.5278 |
| 8y | 9.50% | 9.819% | 0.4727 |
| 9y | 9.70% | 10.096% | 0.4208 |
| 10y | 9.90% | 10.394% | 0.3720 |

## 2. Bond portfolio

| Bond | Face | Coupon | Price (per 100) | Modified duration | DV01 |
| --- | --- | --- | --- | --- | --- |
| 3-year bond | R50,000,000 | 8.0% | 99.74 | 2.57 | R-12,833 |
| 7-year bond | R80,000,000 | 9.0% | 98.48 | 4.97 | R-39,180 |
| 10-year bond | R70,000,000 | 10.0% | 100.63 | 6.05 | R-42,631 |

**Portfolio value:** R199,096,297. **Portfolio DV01:** R-94,645 per 1bp (the portfolio loses this much if rates rise by 0.01%).

## 3. Swap hedge

Hedge with a 7-year **payer swap** (pay fixed, receive compounded ZARONIA), which gains when rates rise.

- Par swap rate: 9.300%
- Swap DV01 per R1 notional: 494.8 per R1 million
- **Hedge notional: R191,265,903**, sized so the swap's DV01 offsets the portfolio's.

## 4. Scenarios

| Scenario | Bond portfolio P&L | Swap hedge P&L | Net P&L |
| --- | --- | --- | --- |
| Parallel +100bp | R-9,139,461 | R9,158,291 | R18,830 |
| Parallel -100bp | R9,809,028 | R-9,786,999 | R22,030 |
| Bear steepener (short end flat, 10y +100bp) | R-5,852,290 | R5,412,188 | R-440,102 |
| Bull flattener (short end flat, 10y -100bp) | R6,262,040 | R-5,661,525 | R600,515 |
| Twist (1y +50bp, 10y -50bp) | R1,360,836 | R-811,521 | R549,315 |

**Reading the table:** a DV01 hedge removes most of the risk from *parallel* moves, but not all of it, because of convexity: bond values change non-linearly for large moves. It also leaves risk when the curve *changes shape*: the bonds' risk is spread across 3, 7 and 10 years, while the hedge sits at 7 years. That leftover is called curve risk, and fixing it means splitting the hedge across several tenors.

## Notes

- JIBAR, the old ZAR reference rate, publishes for the last time on 31 December 2026; ZARONIA is its successor, so the hedge here references compounded ZARONIA.
- Simplifications: annual coupons (SA government bonds pay semi-annually), a single curve for discounting and forecasting, and linear interpolation. Real desks use separate curves and market conventions.