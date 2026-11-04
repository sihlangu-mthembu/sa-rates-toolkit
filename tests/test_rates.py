import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from analytics import carry_rolldown, fit_nelson_siegel, yield_to_maturity  # noqa: E402
from rates import bond_price, bootstrap, dv01, par_swap_rate, swap_value  # noqa: E402
from us_markets import cheapest_to_deliver, conversion_factor  # noqa: E402

PAR = [0.07, 0.075, 0.08, 0.085, 0.09]


class CurveTests(unittest.TestCase):
    def setUp(self):
        self.curve = bootstrap(PAR)

    def test_par_bonds_price_at_100(self):
        for n, y in enumerate(PAR, start=1):
            self.assertAlmostEqual(bond_price(self.curve, y, n), 100.0, places=8)

    def test_nelson_siegel_fits_closely(self):
        _, rmse_bp = fit_nelson_siegel(self.curve.tenors, self.curve.zeros)
        self.assertLess(rmse_bp, 5)


class PricingTests(unittest.TestCase):
    def setUp(self):
        self.curve = bootstrap(PAR)

    def test_par_swap_is_worth_zero(self):
        rate = par_swap_rate(self.curve, 5)
        self.assertAlmostEqual(swap_value(self.curve, rate, 5, 1_000_000), 0.0, places=6)

    def test_payer_swap_gains_and_bond_loses_when_rates_rise(self):
        rate = par_swap_rate(self.curve, 5)
        self.assertGreater(dv01(lambda c: swap_value(c, rate, 5, 1_000_000), self.curve), 0)
        self.assertLess(dv01(lambda c: bond_price(c, 0.08, 5), self.curve), 0)

    def test_ytm_of_par_bond_equals_coupon(self):
        self.assertAlmostEqual(yield_to_maturity(100.0, 0.09, 5), 0.09, places=8)

    def test_rolldown_positive_on_upward_curve(self):
        table = carry_rolldown(self.curve, [{"name": "5y", "coupon": 0.09, "maturity": 5}])
        self.assertGreater(table.loc["5y", "roll_down"], 0)


class FuturesTests(unittest.TestCase):
    def test_conversion_factor_is_one_for_six_percent_coupon(self):
        self.assertAlmostEqual(conversion_factor(0.06, 10), 1.0, places=10)

    def test_ctd_has_lowest_basis(self):
        df = cheapest_to_deliver()
        self.assertTrue(df.iloc[0]["ctd"])
        self.assertTrue(np.all(df["gross_basis"].iloc[0] <= df["gross_basis"]))


if __name__ == "__main__":
    unittest.main()
