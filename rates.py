"""Core rates maths with NumPy: zero-curve bootstrap, discounting, bond and swap pricing, DV01.

Simplifications (stated so they can be discussed, not hidden):
- annual coupons and annual swap payments (SA government bonds actually pay semi-annually);
- one curve for discounting and forecasting (single-curve), with the floating leg modelled as
  compounded overnight ZARONIA, so a floating leg is worth 1 - DF(T) per unit notional;
- linear interpolation of zero rates, annual compounding.
"""

import numpy as np


class ZeroCurve:
    def __init__(self, tenors, zero_rates):
        self.tenors = np.asarray(tenors, dtype=float)
        self.zeros = np.asarray(zero_rates, dtype=float)

    def zero(self, t):
        """Linearly interpolated zero rate; flat beyond the ends. Accepts scalars or arrays."""
        return np.interp(t, self.tenors, self.zeros)

    def df(self, t):
        t = np.asarray(t, dtype=float)
        return (1 + self.zero(t)) ** -t

    def shifted(self, shift_fn):
        """New curve with zero rates moved by shift_fn(tenors) in decimal (0.01 = 100bp)."""
        return ZeroCurve(self.tenors, self.zeros + shift_fn(self.tenors))


def bootstrap(par_yields):
    """Annual par yields at tenors 1..N (array-like) -> ZeroCurve.

    A par bond prices at 1: c * sum(DF_1..DF_n) + DF_n = 1, so
    DF_n = (1 - c * sum(DF_1..DF_{n-1})) / (1 + c).
    """
    c = np.asarray(par_yields, dtype=float)
    dfs = np.empty_like(c)
    for i, ci in enumerate(c):
        dfs[i] = (1 - ci * dfs[:i].sum()) / (1 + ci)
    tenors = np.arange(1, len(c) + 1, dtype=float)
    return ZeroCurve(tenors, dfs ** (-1 / tenors) - 1)


def cash_flows(coupon, maturity, face=100.0, first=1.0):
    """Times and amounts of an annual-coupon bond's remaining cash flows."""
    times = np.arange(first, maturity + 1e-9, 1.0)
    amounts = np.full(times.shape, face * coupon)
    amounts[-1] += face
    return times, amounts


def bond_price(curve, coupon, maturity, face=100.0):
    times, amounts = cash_flows(coupon, maturity, face)
    return float(np.sum(amounts * curve.df(times)))


def annuity(curve, maturity):
    return float(np.sum(curve.df(np.arange(1, maturity + 1))))


def par_swap_rate(curve, maturity):
    return (1 - float(curve.df(maturity))) / annuity(curve, maturity)


def swap_value(curve, fixed_rate, maturity, notional, pay_fixed=True):
    """Value of a fixed vs compounded-overnight swap. A payer swap gains when rates rise."""
    value = ((1 - float(curve.df(maturity))) - fixed_rate * annuity(curve, maturity)) * notional
    return value if pay_fixed else -value


def dv01(value_fn, curve):
    """Value change for a +1bp parallel move (central difference). Gains are positive."""
    up = value_fn(curve.shifted(lambda t: np.full_like(t, 0.0001)))
    down = value_fn(curve.shifted(lambda t: np.full_like(t, -0.0001)))
    return (up - down) / 2


def modified_duration(curve, coupon, maturity):
    price = bond_price(curve, coupon, maturity)
    return -dv01(lambda c: bond_price(c, coupon, maturity), curve) / price / 0.0001
