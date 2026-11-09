"""US rates module: SOFR swap rates and Treasury futures cheapest-to-deliver.

All inputs are ILLUSTRATIVE. Simplifications: annual compounding for SOFR swaps, a simplified
conversion factor (price per 1 of face at a 6% yield with semi-annual coupons, no accrued
interest or delivery-month adjustments) and clean prices given directly.
"""


from typing import Any

import numpy as np
import pandas as pd
from pandas import DataFrame

from rates import bootstrap, par_swap_rate

# Illustrative SOFR OIS par rates, 1 to 10 years (inverted at the front, as when cuts are priced in).
SOFR_PAR = [0.0390, 0.0365, 0.0355, 0.0355, 0.0360, 0.0368, 0.0376, 0.0383, 0.0389, 0.0395]

# Illustrative 10-year note futures deliverable basket.
FUTURES_PRICE = 110.50
BASKET = [
    {"note": "4.000% 2032", "coupon": 0.0400, "years": 6.5, "price": 100.10},
    {"note": "4.250% 2033", "coupon": 0.0425, "years": 7.0, "price": 101.20},
    {"note": "3.875% 2033", "coupon": 0.03875, "years": 7.5, "price": 98.55},
    {"note": "4.375% 2034", "coupon": 0.04375, "years": 8.0, "price": 101.70},
]


def sofr_swap_curve() -> DataFrame:
    curve = bootstrap(SOFR_PAR)
    return pd.DataFrame({"tenor_years": np.arange(1, 11), "sofr_par_swap_rate": [par_swap_rate(curve, n) for n in range(1, 11)],
                         "sofr_zero_rate": curve.zeros}).set_index("tenor_years")


def conversion_factor(coupon: float, years: float, notional_yield: float = 0.06) -> float:
    """Simplified CME-style factor: price of 1 unit of face at a 6% yield, semi-annual coupons."""
    periods = int(round(years * 2))
    t = np.arange(1, periods + 1)
    c = coupon / 2
    y = notional_yield / 2
    return float(np.sum(c / (1 + y) ** t) + 1 / (1 + y) ** periods)


def cheapest_to_deliver(futures_price: float = FUTURES_PRICE, basket: list[dict[str, Any]]=BASKET) -> DataFrame:
    """Gross basis = cash price - futures price x conversion factor. Lowest basis = cheapest to deliver."""
    df = pd.DataFrame(basket).set_index("note")
    df["conversion_factor"] = [conversion_factor(c, y) for c, y in zip(df["coupon"], df["years"])]
    df["invoice_price"] = futures_price * df["conversion_factor"]
    df["gross_basis"] = df["price"] - df["invoice_price"]
    df["ctd"] = df["gross_basis"] == df["gross_basis"].min()
    return df.sort_values("gross_basis")
