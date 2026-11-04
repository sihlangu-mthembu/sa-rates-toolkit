"""Core rates maths: zero curve bootstrap, bond pricing, swap pricing and DV01. Pure Python.

Simplifications (stated so they can be discussed, not hidden):
- annual coupons and annual swap payments (SA government bonds actually pay semi-annually);
- one curve for discounting and forecasting (single-curve), with the floating leg modelled as
  compounded overnight ZARONIA, so a floating leg is worth 1 - DF(T) per unit notional;
- linear interpolation of zero rates, annual compounding.
"""


class ZeroCurve:
    def __init__(self, tenors, zero_rates):
        self.tenors = list(tenors)
        self.zeros = list(zero_rates)

    def zero(self, t):
        ts, zs = self.tenors, self.zeros
        if t <= ts[0]:
            return zs[0]
        if t >= ts[-1]:
            return zs[-1]
        for (t0, z0), (t1, z1) in zip(zip(ts, zs), zip(ts[1:], zs[1:])):
            if t0 <= t <= t1:
                return z0 + (z1 - z0) * (t - t0) / (t1 - t0)

    def df(self, t):
        return (1 + self.zero(t)) ** -t

    def shifted(self, shift_fn):
        """New curve with zero rates moved by shift_fn(tenor), in decimal (0.01 = 100bp)."""
        return ZeroCurve(self.tenors, [z + shift_fn(t) for t, z in zip(self.tenors, self.zeros)])


def bootstrap(par_yields):
    """Annual par yields {1: y1, 2: y2, ...} at consecutive whole years -> ZeroCurve.

    A par bond prices at 100: c * sum(DF_1..DF_n) + DF_n = 1, so
    DF_n = (1 - c * sum(DF_1..DF_{n-1})) / (1 + c).
    """
    tenors = sorted(par_yields)
    if tenors != list(range(1, len(tenors) + 1)):
        raise ValueError("bootstrap needs consecutive annual tenors starting at 1")
    dfs, zeros = [], []
    for n in tenors:
        c = par_yields[n]
        df_n = (1 - c * sum(dfs)) / (1 + c)
        dfs.append(df_n)
        zeros.append(df_n ** (-1 / n) - 1)
    return ZeroCurve(tenors, zeros)


def bond_price(curve, coupon, maturity, face=100.0):
    """Price of an annual-coupon bond off the curve."""
    cash_flows = [(t, face * coupon) for t in range(1, maturity + 1)]
    cash_flows[-1] = (maturity, face * (1 + coupon))
    return sum(cf * curve.df(t) for t, cf in cash_flows)


def swap_value(curve, fixed_rate, maturity, notional, pay_fixed=True):
    """Value of a vanilla fixed vs compounded-ZARONIA swap to the holder.

    Fixed leg = rate x sum of DFs; floating leg = 1 - DF(T) (per unit notional).
    A payer swap (pay fixed, receive floating) gains when rates rise.
    """
    annuity = sum(curve.df(t) for t in range(1, maturity + 1))
    floating = 1 - curve.df(maturity)
    fixed = fixed_rate * annuity
    value = (floating - fixed) * notional
    return value if pay_fixed else -value


def par_swap_rate(curve, maturity):
    annuity = sum(curve.df(t) for t in range(1, maturity + 1))
    return (1 - curve.df(maturity)) / annuity


def dv01(value_fn, curve):
    """Change in value for a +1bp parallel move in the zero curve (sign: gain is positive)."""
    up = value_fn(curve.shifted(lambda t: 0.0001))
    down = value_fn(curve.shifted(lambda t: -0.0001))
    return (up - down) / 2


def modified_duration(curve, coupon, maturity):
    price = bond_price(curve, coupon, maturity)
    return -dv01(lambda c: bond_price(c, coupon, maturity), curve) / price / 0.0001
