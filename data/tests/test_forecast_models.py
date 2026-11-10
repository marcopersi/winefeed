"""1.3: forecast.models.fit_provider_effects against a synthetic,
noiseless dataset with known ground truth -- OLS must recover the
designed coefficients exactly (up to floating point)."""
import datetime
import math
import sqlite3
import unittest

import build_db
from forecast import models


class FitProviderEffectsTest(unittest.TestCase):
    RECENT = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()

    # True (pre-centering) provider log-offsets: koppe is the implicit
    # reference (0.0) in this hand-picked design.
    TRUE_OFFSET = {"koppe": 0.0, "langtons": 0.10, "christies": -0.05}
    TRUE_QTY_COEF = -0.20
    TRUE_SIZE_ASSUMED_COEF = -0.05
    # One "true value" per (wine_ref_id, vintage) group (size_class is
    # part of the FE group too, but every row here uses 7.5dl so the
    # group key collapses to wine_ref_id/vintage for this test).
    TRUE_GROUP_VALUE = {1: 5.0, 2: 5.5, 3: 4.7, 4: 6.0}

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(build_db.SCHEMA)
        self.builder = build_db.Builder(self.conn)
        self.auction_id = {
            name: self.builder.add_auction(name, "1", "x", None, "EUR",
                                           "HAMMER")
            for name in self.TRUE_OFFSET
        }
        self._lot_no = 0

    def tearDown(self):
        self.conn.close()

    def _add_row(self, wine_ref_id, provider, qty, size_assumed,
                 group_value=None):
        if group_value is None:
            group_value = self.TRUE_GROUP_VALUE[wine_ref_id]
        true_y = (group_value
                  + self.TRUE_OFFSET[provider]
                  + self.TRUE_QTY_COEF * math.log(qty)
                  + self.TRUE_SIZE_ASSUMED_COEF * size_assumed)
        price = math.exp(true_y)
        self._lot_no += 1
        lot_id = self.builder.add_lot(self.auction_id[provider], {
            "lot_no": str(self._lot_no), "wine": "test-wine",
            "wine_ref_id": wine_ref_id, "bottle_size_dl": 7.5,
            "quantity": qty, "lot_date": self.RECENT, "sold": 1,
            "hammer_price": price})
        # size_assumed's CHECK constraint only allows NULL or 1 (there is
        # no explicit stored 0 -- "not assumed" is NULL, matching how
        # _assume_default_bottle_size itself only ever writes 1).
        self.conn.execute(
            "UPDATE lots SET lot_kind='SINGLE', vintage_status='STRUCTURED',"
            " vintage_final=2015, price_per_bottle_eur=?, quantity=?,"
            " size_assumed=? WHERE id=?",
            (price, qty, (1 if size_assumed else None), lot_id))

    def _populate_balanced_design(self):
        # Every (wine_ref_id, provider, qty, size_assumed) combination
        # appears exactly once -- a fully balanced design, so the
        # observation-weighted mean recentering is a plain arithmetic
        # mean, easy to check by hand.
        for wine_ref_id in self.TRUE_GROUP_VALUE:
            for provider in self.TRUE_OFFSET:
                for qty in (1, 3):
                    for size_assumed in (0, 1):
                        self._add_row(wine_ref_id, provider, qty,
                                     size_assumed)

    def test_recovers_known_offsets_exactly(self):
        self._populate_balanced_design()
        offsets, report = models.fit_provider_effects(self.conn)

        expected_mean = sum(self.TRUE_OFFSET.values()) / len(self.TRUE_OFFSET)
        expected = {p: v - expected_mean
                    for p, v in self.TRUE_OFFSET.items()}

        got = dict(zip(offsets["provider"], offsets["offset"]))
        self.assertEqual(set(got), set(expected))
        for provider, exp_val in expected.items():
            self.assertAlmostEqual(got[provider], exp_val, places=6)

        # Centered: the observation-weighted mean of the recovered
        # offsets is 0 (balanced design here, so a plain mean).
        self.assertAlmostEqual(sum(got.values()) / len(got), 0.0, places=6)

    def test_offsets_sum_to_zero_even_with_unbalanced_counts(self):
        # Same design, but christies gets 3x the rows -- the recovered
        # offsets must still be an OBSERVATION-weighted mean of 0, not
        # a plain unweighted mean of 0 (those differ once counts are
        # unequal across providers).
        self._populate_balanced_design()
        for _ in range(2):
            for wine_ref_id in self.TRUE_GROUP_VALUE:
                for qty in (1, 3):
                    for size_assumed in (0, 1):
                        self._add_row(wine_ref_id, "christies", qty,
                                     size_assumed)
        offsets, _ = models.fit_provider_effects(self.conn)
        got = dict(zip(offsets["provider"], offsets["offset"]))
        n = dict(zip(offsets["provider"], offsets["n_obs"]))
        weighted_sum = sum(got[p] * n[p] for p in got)
        self.assertAlmostEqual(weighted_sum, 0.0, places=5)
        # Still recovers the true relative gap between providers.
        self.assertAlmostEqual(
            got["langtons"] - got["christies"],
            self.TRUE_OFFSET["langtons"] - self.TRUE_OFFSET["christies"],
            places=6)

    def test_variance_report_residual_lower_than_within(self):
        self._populate_balanced_design()
        _, report = models.fit_provider_effects(self.conn)
        self.assertGreater(report["var_within_before"], 0)
        # Noiseless synthetic data: the model explains everything.
        self.assertAlmostEqual(report["var_residual_after"], 0.0, places=6)
        self.assertLess(report["var_residual_after"],
                        report["var_within_before"])

    def test_singleton_groups_are_dropped_not_crashing(self):
        # A (wine_ref_id, vintage, size_class) group with exactly one
        # observation contributes nothing to a within estimator and
        # must not crash the fit.
        self._add_row(99, "koppe", 1, 0, group_value=5.0)
        self._populate_balanced_design()
        offsets, report = models.fit_provider_effects(self.conn)
        self.assertFalse(offsets.empty)
        self.assertFalse(math.isnan(report["var_within_before"]))

    def test_empty_input_does_not_crash(self):
        offsets, report = models.fit_provider_effects(self.conn)
        self.assertTrue(offsets.empty)
        self.assertTrue(math.isnan(report["var_within_before"]))


if __name__ == "__main__":
    unittest.main()
