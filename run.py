"""sa-rates-toolkit: build a ZAR zero curve, value a bond portfolio, size a ZARONIA swap hedge, run scenarios.

Usage:  python run.py      -> reports/report.md and reports/curve.svg

All market inputs are ILLUSTRATIVE (round numbers in the general range of South African
government bond yields in 2025-26). They are not live market data.
"""

import datetime
import pathlib

from rates import bond_price, bootstrap, dv01, modified_duration, par_swap_rate, swap_value

ROOT = pathlib.Path(__file__).resolve().parent

# Illustrative annual par yields, 1 to 10 years (upward sloping, like the ZAR curve).
PAR_YIELDS = {1: 0.075, 2: 0.078, 3: 0.081, 4: 0.084, 5: 0.087, 6: 0.090, 7: 0.093, 8: 0.095, 9: 0.097, 10: 0.099}

# Illustrative portfolio: face value in rand, annual coupon, maturity in years.
PORTFOLIO = [
    {"name": "3-year bond", "face": 50_000_000, "coupon": 0.080, "maturity": 3},
    {"name": "7-year bond", "face": 80_000_000, "coupon": 0.090, "maturity": 7},
    {"name": "10-year bond", "face": 70_000_000, "coupon": 0.100, "maturity": 10},
]
HEDGE_TENOR = 7

SCENARIOS = {
    "Parallel +100bp": lambda t: 0.01,
    "Parallel -100bp": lambda t: -0.01,
    "Bear steepener (short end flat, 10y +100bp)": lambda t: 0.01 * (t - 1) / 9,
    "Bull flattener (short end flat, 10y -100bp)": lambda t: -0.01 * (t - 1) / 9,
    "Twist (1y +50bp, 10y -50bp)": lambda t: 0.005 - 0.01 * (t - 1) / 9,
}


def portfolio_value(curve):
    return sum(bond_price(curve, b["coupon"], b["maturity"], face=1) * b["face"] for b in PORTFOLIO)


def money(x):
    return f"R{x:,.0f}"


def curve_svg(curve, path):
    w, h, pad = 520, 260, 40
    zs = curve.zeros
    lo, hi = min(zs) - 0.005, max(zs) + 0.005
    pts = [(pad + (t - 1) / 9 * (w - 2 * pad), h - pad - (z - lo) / (hi - lo) * (h - 2 * pad)) for t, z in zip(curve.tenors, zs)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    labels = "".join(f'<text x="{x:.1f}" y="{h - pad + 16}" font-size="11" text-anchor="middle">{t}y</text>'
                     for (x, _), t in zip(pts, curve.tenors))
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3"/>' for x, y in pts)
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="sans-serif">'
        f'<rect width="100%" height="100%" fill="white"/>'
        f'<text x="{pad}" y="22" font-size="13">Bootstrapped ZAR zero curve (illustrative inputs)</text>'
        f'<polyline points="{poly}" fill="none" stroke="#1f6feb" stroke-width="2"/>{dots}{labels}'
        f'<text x="{pad}" y="{pad - 4}" font-size="11">{hi:.1%}</text>'
        f'<text x="{pad}" y="{h - pad - 4}" font-size="11">{lo:.1%}</text></svg>', encoding="utf-8")


def main():
    curve = bootstrap(PAR_YIELDS)
    base = portfolio_value(curve)
    port_dv01 = dv01(portfolio_value, curve)

    swap_rate = par_swap_rate(curve, HEDGE_TENOR)
    swap_dv01_per_rand = dv01(lambda c: swap_value(c, swap_rate, HEDGE_TENOR, 1.0, pay_fixed=True), curve)
    hedge_notional = -port_dv01 / swap_dv01_per_rand

    def hedge_value(c):
        return swap_value(c, swap_rate, HEDGE_TENOR, hedge_notional, pay_fixed=True)

    lines = ["# SA rates toolkit report", "",
             f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M}. **All market inputs are illustrative, not live data.**", "",
             "## 1. Zero curve", "",
             "Bootstrapped from annual par yields. ![curve](curve.svg)", "",
             "| Tenor | Par yield | Zero rate | Discount factor |", "| --- | --- | --- | --- |"]
    for t in curve.tenors:
        lines.append(f"| {t}y | {PAR_YIELDS[t]:.2%} | {curve.zero(t):.3%} | {curve.df(t):.4f} |")

    lines += ["", "## 2. Bond portfolio", "",
              "| Bond | Face | Coupon | Price (per 100) | Modified duration | DV01 |", "| --- | --- | --- | --- | --- | --- |"]
    for b in PORTFOLIO:
        price = bond_price(curve, b["coupon"], b["maturity"])
        md = modified_duration(curve, b["coupon"], b["maturity"])
        b_dv01 = dv01(lambda c, b=b: bond_price(c, b["coupon"], b["maturity"], face=1) * b["face"], curve)
        lines.append(f"| {b['name']} | {money(b['face'])} | {b['coupon']:.1%} | {price:.2f} | {md:.2f} | {money(b_dv01)} |")
    lines += ["", f"**Portfolio value:** {money(base)}. **Portfolio DV01:** {money(port_dv01)} per 1bp "
              "(the portfolio loses this much if rates rise by 0.01%)."]

    lines += ["", "## 3. Swap hedge", "",
              f"Hedge with a {HEDGE_TENOR}-year **payer swap** (pay fixed, receive compounded ZARONIA), which gains when rates rise.", "",
              f"- Par swap rate: {swap_rate:.3%}",
              f"- Swap DV01 per R1 notional: {swap_dv01_per_rand * 1e6:,.1f} per R1 million",
              f"- **Hedge notional: {money(hedge_notional)}**, sized so the swap's DV01 offsets the portfolio's."]

    lines += ["", "## 4. Scenarios", "",
              "| Scenario | Bond portfolio P&L | Swap hedge P&L | Net P&L |", "| --- | --- | --- | --- |"]
    for name, fn in SCENARIOS.items():
        shocked = curve.shifted(fn)
        p = portfolio_value(shocked) - base
        s = hedge_value(shocked) - hedge_value(curve)
        lines.append(f"| {name} | {money(p)} | {money(s)} | {money(p + s)} |")
    lines += ["",
              "**Reading the table:** a DV01 hedge removes most of the risk from *parallel* moves, but not all of it, "
              "because of convexity: bond values change non-linearly for large moves. It also leaves risk when the "
              "curve *changes shape*: the bonds' risk is spread across 3, 7 and 10 years, while the hedge sits at 7 years. "
              "That leftover is called curve risk, and fixing it means splitting the hedge across several tenors.",
              "", "## Notes", "",
              "- JIBAR, the old ZAR reference rate, publishes for the last time on 31 December 2026; ZARONIA is its "
              "successor, so the hedge here references compounded ZARONIA.",
              "- Simplifications: annual coupons (SA government bonds pay semi-annually), a single curve for "
              "discounting and forecasting, and linear interpolation. Real desks use separate curves and market conventions."]

    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "report.md").write_text("\n".join(lines), encoding="utf-8")
    curve_svg(curve, ROOT / "reports" / "curve.svg")
    print("\n".join(l for l in lines if l.startswith("**Portfolio") or l.startswith("- **Hedge") or l.startswith("| Parallel") or l.startswith("| Bear") or l.startswith("| Twist")))


if __name__ == "__main__":
    main()
