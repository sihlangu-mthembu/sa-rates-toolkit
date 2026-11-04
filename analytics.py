"""Analytics with SciPy and pandas: Nelson-Siegel fit, yield to maturity, carry and roll-down."""

import numpy as np
import pandas as pd
from scipy.optimize import brentq, least_squares

from rates import bond_price, cash_flows


def nelson_siegel(t, beta0, beta1, beta2, tau):
    """Nelson-Siegel zero rate: level (beta0), slope (beta1) and curvature (beta2)."""
    t = np.asarray(t, dtype=float)
    x = t / tau
    loading = (1 - np.exp(-x)) / x
    return beta0 + beta1 * loading + beta2 * (loading - np.exp(-x))


def fit_nelson_siegel(tenors, zeros):
    """Least-squares fit of the four Nelson-Siegel parameters. Returns (params, rmse_bp)."""
    def residuals(p):
        return nelson_siegel(tenors, *p) - zeros

    fit = least_squares(residuals, x0=[zeros[-1], zeros[0] - zeros[-1], 0.0, 2.0],
                        bounds=([-1, -1, -1, 0.05], [1, 1, 1, 30]))
    rmse_bp = float(np.sqrt(np.mean(fit.fun ** 2)) * 1e4)
    return dict(zip(["beta0 (level)", "beta1 (slope)", "beta2 (curvature)", "tau"], fit.x)), rmse_bp


def yield_to_maturity(price, coupon, maturity, face=100.0):
    """Solve for the single annual yield that discounts the bond's cash flows to its price."""
    times, amounts = cash_flows(coupon, maturity, face)

    def gap(y):
        return float(np.sum(amounts / (1 + y) ** times)) - price

    return brentq(gap, -0.5, 1.0)


def carry_rolldown(curve, bonds, horizon=1.0):
    """One-year return decomposition for each bond if the curve does NOT move.

    carry      = coupon income / price  minus the cost of funding the position at the 1-year rate
    roll-down  = price change from the bond ageing one year along an unchanged curve
                 (it is now priced at a shorter, usually lower-yielding, point on the curve)
    """
    funding = float(curve.zero(horizon))
    rows = []
    for b in bonds:
        p0 = bond_price(curve, b["coupon"], b["maturity"])
        p1 = bond_price(curve, b["coupon"], b["maturity"] - horizon) if b["maturity"] > horizon else 100.0
        coupon_income = 100 * b["coupon"]
        carry = coupon_income / p0 - funding
        roll = (p1 - p0) / p0
        rows.append({"bond": b["name"], "price": p0, "carry": carry, "roll_down": roll,
                     "carry_plus_roll": carry + roll})
    return pd.DataFrame(rows).set_index("bond")
