"""sa-rates-toolkit: ZAR curve, bond portfolio risk, ZARONIA swap hedge, carry/roll-down,
Nelson-Siegel fit, plus a US module (SOFR swaps, Treasury futures cheapest-to-deliver).

Usage:  pip install -r requirements.txt
        python run.py      -> reports/report.md and reports/curve.svg

All market inputs are ILLUSTRATIVE, not live market data.
"""

import datetime
import pathlib

import numpy as np
import pandas as pd

from analytics import carry_rolldown, fit_nelson_siegel, nelson_siegel, yield_to_maturity
from rates import bond_price, bootstrap, dv01, modified_duration, par_swap_rate, swap_value
from us_markets import FUTURES_PRICE, cheapest_to_deliver, sofr_swap_curve

ROOT = pathlib.Path(__file__).resolve().parent

# Illustrative ZAR par yields, 1-10 years (upward sloping).
PAR_YIELDS = [0.075, 0.078, 0.081, 0.084, 0.087, 0.090, 0.093, 0.095, 0.097, 0.099]

PORTFOLIO = pd.DataFrame([
    {"name": "3-year bond", "face": 50_000_000, "coupon": 0.080, "maturity": 3},
    {"name": "7-year bond", "face": 80_000_000, "coupon": 0.090, "maturity": 7},
    {"name": "10-year bond", "face": 70_000_000, "coupon": 0.100, "maturity": 10},
])
HEDGE_TENOR = 7

SCENARIOS = {
    "Parallel +100bp": lambda t: np.full_like(t, 0.01),
    "Parallel -100bp": lambda t: np.full_like(t, -0.01),
    "Bear steepener (10y +100bp)": lambda t: 0.01 * (t - 1) / 9,
    "Bull flattener (10y -100bp)": lambda t: -0.01 * (t - 1) / 9,
    "Twist (1y +50bp, 10y -50bp)": lambda t: 0.005 - 0.01 * (t - 1) / 9,
}


def portfolio_value(curve):
    return sum(bond_price(curve, r.coupon, r.maturity, face=1) * r.face for r in PORTFOLIO.itertuples())


def md_table(df, formats):
    """Render a DataFrame as a Markdown table, formatting columns with the given format strings."""
    cols = [df.index.name or ""] + list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join("---" for _ in cols) + " |"]
    for idx, row in df.iterrows():
        cells = [str(idx)] + [formats.get(c, "{}").format(row[c]) for c in df.columns]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def curve_svg(curve, ns_params, path):
    w, h, pad = 540, 270, 44
    fine = np.linspace(1, 10, 91)
    ns = nelson_siegel(fine, *ns_params.values())
    lo, hi = min(curve.zeros.min(), ns.min()) - 0.004, max(curve.zeros.max(), ns.max()) + 0.004

    def xy(t, z):
        return pad + (t - 1) / 9 * (w - 2 * pad), h - pad - (z - lo) / (hi - lo) * (h - 2 * pad)

    boot = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(t, z) for t, z in zip(curve.tenors, curve.zeros)))
    fit = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(t, z) for t, z in zip(fine, ns)))
    ticks = "".join(f'<text x="{xy(t, lo)[0]:.1f}" y="{h - pad + 16}" font-size="11" text-anchor="middle">{int(t)}y</text>'
                    for t in curve.tenors)
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" font-family="sans-serif">'
        f'<rect width="100%" height="100%" fill="white"/>'
        f'<text x="{pad}" y="20" font-size="13">ZAR zero curve: bootstrapped (dots) vs Nelson-Siegel fit (line)</text>'
        f'<polyline points="{fit}" fill="none" stroke="#d1242f" stroke-width="1.5"/>'
        f'<polyline points="{boot}" fill="none" stroke="#1f6feb" stroke-width="2" stroke-dasharray="4 3"/>'
        + "".join(f'<circle cx="{p.split(",")[0]}" cy="{p.split(",")[1]}" r="3" fill="#1f6feb"/>' for p in boot.split())
        + ticks + f'<text x="4" y="{pad}" font-size="11">{hi:.1%}</text>'
        f'<text x="4" y="{h - pad}" font-size="11">{lo:.1%}</text></svg>', encoding="utf-8")


def main():
    curve = bootstrap(PAR_YIELDS)
    ns_params, ns_rmse = fit_nelson_siegel(curve.tenors, curve.zeros)

    curve_df = pd.DataFrame({"par_yield": PAR_YIELDS, "zero_rate": curve.zeros, "discount_factor": curve.df(curve.tenors),
                             "nelson_siegel": nelson_siegel(curve.tenors, *ns_params.values())},
                            index=pd.Index([f"{int(t)}y" for t in curve.tenors], name="tenor"))

    port = PORTFOLIO.set_index("name")
    port["price"] = [bond_price(curve, r.coupon, r.maturity) for r in PORTFOLIO.itertuples()]
    port["ytm"] = [yield_to_maturity(p, c, m) for p, c, m in zip(port["price"], port["coupon"], port["maturity"])]
    port["mod_duration"] = [modified_duration(curve, r.coupon, r.maturity) for r in PORTFOLIO.itertuples()]
    port["dv01"] = [dv01(lambda c, r=r: bond_price(c, r.coupon, r.maturity, face=1) * r.face, curve) for r in PORTFOLIO.itertuples()]
    port.index.name = "bond"
    base, port_dv01 = portfolio_value(curve), port["dv01"].sum()

    swap_rate = par_swap_rate(curve, HEDGE_TENOR)
    hedge_notional = -port_dv01 / dv01(lambda c: swap_value(c, swap_rate, HEDGE_TENOR, 1.0), curve)

    def hedge_value(c):
        return swap_value(c, swap_rate, HEDGE_TENOR, hedge_notional)

    scen = pd.DataFrame(
        [{"scenario": name, "bonds": portfolio_value(curve.shifted(fn)) - base,
          "swap_hedge": hedge_value(curve.shifted(fn)) - hedge_value(curve)} for name, fn in SCENARIOS.items()]
    ).set_index("scenario")
    scen["net"] = scen["bonds"] + scen["swap_hedge"]

    carry = carry_rolldown(curve, PORTFOLIO.to_dict("records"))
    sofr = sofr_swap_curve()
    ctd = cheapest_to_deliver()

    rand = "R{:,.0f}"
    pct = "{:.2%}"
    lines = ["# SA rates toolkit report", "",
             f"Generated {datetime.datetime.now():%Y-%m-%d %H:%M}. **All market inputs are illustrative, not live data.**",
             "", "## 1. ZAR zero curve", "", "![curve](curve.svg)", ""]
    lines += md_table(curve_df, {"par_yield": pct, "zero_rate": "{:.3%}", "discount_factor": "{:.4f}", "nelson_siegel": "{:.3%}"})
    lines += ["", "Nelson-Siegel fit (SciPy least squares): " +
              ", ".join(f"{k} = {v:.4f}" for k, v in ns_params.items()) + f"; RMSE {ns_rmse:.1f}bp. "
              "Three parameters summarise the whole curve as level, slope and curvature, which is how curve moves are "
              "usually described and traded."]

    lines += ["", "## 2. Bond portfolio", ""]
    lines += md_table(port[["face", "coupon", "price", "ytm", "mod_duration", "dv01"]],
                      {"face": rand, "coupon": "{:.1%}", "price": "{:.2f}", "ytm": pct, "mod_duration": "{:.2f}", "dv01": rand})
    lines += ["", f"**Portfolio value:** {rand.format(base)}. **DV01:** {rand.format(port_dv01)} per 1bp. "
              "Yields to maturity are solved with SciPy's brentq root finder."]

    lines += ["", "## 3. Carry and roll-down (1 year, curve unchanged)", ""]
    lines += md_table(carry, {"price": "{:.2f}", "carry": pct, "roll_down": pct, "carry_plus_roll": pct})
    lines += ["", "Carry is coupon income minus the cost of funding the bond at the 1-year rate. Roll-down is the price "
              "gain from the bond ageing along an upward-sloping curve: next year it is priced at a shorter, lower-yielding "
              "point. Together they are the return earned if nothing moves, and a common starting point for relative-value "
              "comparisons along the curve."]

    lines += ["", "## 4. ZARONIA swap hedge and scenarios", "",
              f"7-year payer swap (pay fixed {swap_rate:.3%}, receive compounded ZARONIA), notional "
              f"**{rand.format(hedge_notional)}**, sized so its DV01 offsets the portfolio's.", ""]
    lines += md_table(scen, {"bonds": rand, "swap_hedge": rand, "net": rand})
    lines += ["", "The hedge neutralises parallel moves up to a small convexity residual, but leaves curve risk under "
              "steepeners and twists, because the bonds' risk is spread across 3, 7 and 10 years while the hedge sits at 7."]

    lines += ["", "## 5. US module: SOFR swaps", ""]
    lines += md_table(sofr, {"sofr_par_swap_rate": "{:.3%}", "sofr_zero_rate": "{:.3%}"})
    lines += ["", "An illustrative SOFR OIS curve, inverted at the front as when rate cuts are priced in. SOFR replaced "
              "USD LIBOR, as ZARONIA is replacing JIBAR."]

    lines += ["", "## 6. US module: Treasury futures cheapest-to-deliver", "",
              f"10-year note futures price {FUTURES_PRICE:.2f}. Gross basis = cash price - futures price x conversion factor.", ""]
    lines += md_table(ctd[["coupon", "years", "price", "conversion_factor", "invoice_price", "gross_basis", "ctd"]],
                      {"coupon": "{:.3%}", "years": "{:.1f}", "price": "{:.2f}", "conversion_factor": "{:.4f}",
                       "invoice_price": "{:.2f}", "gross_basis": "{:.2f}", "ctd": "{}"})
    lines += ["", "The note with the lowest gross basis is cheapest to deliver; futures prices and hedge ratios track it. "
              "Simplified: no accrued interest, implied repo or delivery options."]

    lines += ["", "## Notes", "",
              "- JIBAR publishes for the last time on 31 December 2026; ZARONIA is its successor.",
              "- Simplifications: annual coupons for ZAR bonds, single-curve framework, linear interpolation, illustrative inputs."]

    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "report.md").write_text("\n".join(lines), encoding="utf-8")
    curve_svg(curve, ns_params, ROOT / "reports" / "curve.svg")
    print(f"Portfolio DV01 {rand.format(port_dv01)}; hedge notional {rand.format(hedge_notional)}; "
          f"Nelson-Siegel RMSE {ns_rmse:.1f}bp; CTD: {ctd.index[0]}")
    print(carry.round(4).to_string())


if __name__ == "__main__":
    main()
