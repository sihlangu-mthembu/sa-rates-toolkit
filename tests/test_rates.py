import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from rates import bond_price, bootstrap, dv01, par_swap_rate, swap_value  # noqa: E402

PAR = {1: 0.07, 2: 0.075, 3: 0.08, 4: 0.085, 5: 0.09}


class CurveTests(unittest.TestCase):
    def setUp(self):
        self.curve = bootstrap(PAR)

    def test_par_bonds_price_at_100(self):
        # The defining property of a bootstrapped curve: it reprices its own inputs.
        for n, y in PAR.items():
            self.assertAlmostEqual(bond_price(self.curve, y, n), 100.0, places=8)

    def test_upward_par_curve_gives_zeros_above_par(self):
        self.assertGreater(self.curve.zero(5), PAR[5])


class SwapTests(unittest.TestCase):
    def setUp(self):
        self.curve = bootstrap(PAR)

    def test_par_swap_is_worth_zero(self):
        rate = par_swap_rate(self.curve, 5)
        self.assertAlmostEqual(swap_value(self.curve, rate, 5, 1_000_000), 0.0, places=6)

    def test_payer_swap_gains_when_rates_rise(self):
        rate = par_swap_rate(self.curve, 5)
        self.assertGreater(dv01(lambda c: swap_value(c, rate, 5, 1_000_000, pay_fixed=True), self.curve), 0)

    def test_bond_loses_when_rates_rise(self):
        self.assertLess(dv01(lambda c: bond_price(c, 0.08, 5), self.curve), 0)


if __name__ == "__main__":
    unittest.main()
