"""forecast.calibrate -- Stufe 4.1 (Split-Conformal) als reine
Funktionen ueber einem synthetischen ``eval.evaluate``-Rueckgabe-
DataFrame, keine DB noetig (dieselbe Shape wie eval.py's echte
Pro-Ziel-Zeilen: ``origin``, ``density_class``, ``y_true``, ``q0.5``,
...)."""
# pylint: disable=protected-access
# -- protected-access: exercising calibrate's internal
# _correction/_split_fit_test/_conformal_order_stat/_KNOWN_DENSITY_CLASSES.
import unittest

import pandas as pd

from forecast import calibrate


def _rows(records):
    return pd.DataFrame(records)


# >=19 residuals are needed for a valid 95% conformal threshold
# (ceil(20*0.95)=19 <= 19); 0.00, 0.05, ..., 0.95 gives exactly 20,
# deterministic order statistics for every level below.
_BIG_RESID_SET = [round(0.05 * i, 2) for i in range(20)]


def _big_pooled_rows(density_class="3-4"):
    return [{"density_class": density_class, "y_true": 1.0 + r, "q0.5": 1.0}
           for r in _BIG_RESID_SET]


class ConformalOrderStatTest(unittest.TestCase):
    def test_is_the_kth_smallest_not_an_interpolated_quantile(self):
        # n=5, level=0.8 -> k=ceil(6*0.8)=5 -> the MAXIMUM, never an
        # interpolated value strictly below it.
        residuals = [0.0, 0.2, 0.4, 0.6, 0.8]
        self.assertEqual(
            calibrate._conformal_order_stat(residuals, 0.8), 0.8)

    def test_returns_none_when_rank_exceeds_sample_size(self):
        # n=5, level=0.95 -> k=ceil(6*0.95)=6 > 5.
        residuals = [0.0, 0.2, 0.4, 0.6, 0.8]
        self.assertIsNone(calibrate._conformal_order_stat(residuals, 0.95))

    def test_empty_input_returns_none(self):
        self.assertIsNone(calibrate._conformal_order_stat([], 0.5))


class FitTableTests(unittest.TestCase):
    def test_correction_is_conformal_order_statistic_of_absolute_residual(self):
        # All 20 rows share density_class "3-4", so it also IS the
        # pooled split -- no fallback involved, deterministic order
        # stats for every level.
        df = _rows(_big_pooled_rows())
        table = calibrate.fit_table(df)
        # level=0.5 -> k=ceil(21*0.5)=11 -> 11th smallest (0-indexed 10)
        # of sorted(_BIG_RESID_SET) = 0.50.
        self.assertAlmostEqual(table["3-4"]["0.5"], 0.50)
        # level=0.95 -> k=ceil(21*0.95)=20 -> the maximum, 0.95.
        self.assertAlmostEqual(table["3-4"]["0.95"], 0.95)

    def test_pooled_fallback_used_for_class_missing_from_fit_split(self):
        df = _rows(_big_pooled_rows("10+"))
        table = calibrate.fit_table(df)
        # "1-2" never appears in this split at all.
        self.assertEqual(
            calibrate._correction(table, "1-2", 0.5),
            table["_pooled"]["0.5"])

    def test_class_with_too_few_residuals_falls_back_to_pooled_entirely(self):
        # density_class "1-2" has only 2 residuals of its own (not
        # enough for a valid 95% threshold, k=ceil(3*0.95)=3>2) --
        # review fix: ALL THREE of its levels must come from "_pooled",
        # not just the failing one (never mix a class-specific 50/80%
        # with a pooled 95%, which could cross bands).
        df = _rows(
            _big_pooled_rows("3-4")
            + [{"density_class": "1-2", "y_true": 1.0, "q0.5": 1.0},
               {"density_class": "1-2", "y_true": 1.5, "q0.5": 1.0}])
        table = calibrate.fit_table(df)
        self.assertEqual(table["1-2"], table["_pooled"])
        # Sanity: "3-4" (plenty of its own evidence) computes its own
        # correction directly, not merely by coincidentally matching
        # the pooled fallback.
        self.assertEqual(table["3-4"]["0.5"], 0.50)

    def test_every_known_density_class_has_an_entry(self):
        # Review fix: a future Stage-5 reader indexes calibration_table.json
        # directly (table[dclass]), so every eval._DENSITY_BINS label (plus
        # "10+") must be present even when absent from THIS fit split.
        df = _rows(_big_pooled_rows("10+"))
        table = calibrate.fit_table(df)
        for dclass in calibrate._KNOWN_DENSITY_CLASSES:
            self.assertIn(dclass, table)
        self.assertEqual(table["1-2"], table["_pooled"])

    def test_raises_when_pooled_itself_has_too_few_residuals(self):
        # Only 2 residuals total -- not even the pooled fallback can
        # support a valid 95% threshold (k=ceil(3*0.95)=3>2). Silently
        # using an invalid threshold would be worse than failing loud.
        df = _rows([
            {"density_class": "10+", "y_true": 1.0, "q0.5": 1.0},
            {"density_class": "10+", "y_true": 1.5, "q0.5": 1.0},
        ])
        with self.assertRaises(ValueError):
            calibrate.fit_table(df)


class HeldOutCoverageTests(unittest.TestCase):
    def test_coverage_counts_fraction_within_correction(self):
        table = {"_pooled": {"0.5": 0.3, "0.8": 0.3, "0.95": 0.3}}
        # residuals: 0.1 (inside), 0.2 (inside), 0.4 (outside) -> 2/3.
        df = _rows([
            {"density_class": "5-9", "y_true": 1.1, "q0.5": 1.0},
            {"density_class": "5-9", "y_true": 1.2, "q0.5": 1.0},
            {"density_class": "5-9", "y_true": 1.4, "q0.5": 1.0},
        ])
        coverage = calibrate.held_out_coverage(df, table)
        self.assertEqual(coverage["5-9"]["n"], 3)
        self.assertAlmostEqual(coverage["5-9"]["0.8"], 2 / 3)


class ClassifyTests(unittest.TestCase):
    def test_inside_band_is_forecast(self):
        self.assertEqual(calibrate.classify({"0.8": 0.80}), "forecast")

    def test_outside_band_is_insufficient_data(self):
        self.assertEqual(
            calibrate.classify({"0.8": 0.60}), "INSUFFICIENT_DATA")

    def test_band_edges_are_inclusive(self):
        self.assertEqual(calibrate.classify({"0.8": 0.77}), "forecast")
        self.assertEqual(calibrate.classify({"0.8": 0.83}), "forecast")


class FillMissingDecisionsTests(unittest.TestCase):
    def test_fills_every_known_class_absent_from_test(self):
        decisions = calibrate._fill_missing_decisions({"3-4": "forecast"})
        self.assertEqual(decisions["3-4"], "forecast")
        for dclass in calibrate._KNOWN_DENSITY_CLASSES:
            if dclass != "3-4":
                self.assertEqual(decisions[dclass], "INSUFFICIENT_DATA")

    def test_never_overwrites_an_existing_decision(self):
        decisions = calibrate._fill_missing_decisions(
            {"3-4": "INSUFFICIENT_DATA"})
        self.assertEqual(decisions["3-4"], "INSUFFICIENT_DATA")


class SplitFitTestTests(unittest.TestCase):
    def test_splits_latest_origin_as_test(self):
        df = _rows([
            {"origin": pd.Timestamp("2025-01-01"), "series_key": "a",
             "target_date": pd.Timestamp("2025-02-01"), "y_true": 1.0},
            {"origin": pd.Timestamp("2025-07-01"), "series_key": "b",
             "target_date": pd.Timestamp("2025-08-01"), "y_true": 1.0},
            {"origin": pd.Timestamp("2026-01-01"), "series_key": "c",
             "target_date": pd.Timestamp("2026-02-01"), "y_true": 1.0},
        ])
        fit_origins, test_origin, fit_rows, test_rows = (
            calibrate._split_fit_test(df))
        self.assertEqual(
            fit_origins,
            [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-07-01")])
        self.assertEqual(test_origin, pd.Timestamp("2026-01-01"))
        self.assertEqual(len(fit_rows), 2)
        self.assertEqual(len(test_rows), 1)

    def test_raises_with_a_single_origin(self):
        df = _rows([{"origin": pd.Timestamp("2025-01-01"), "y_true": 1.0,
                     "target_date": pd.Timestamp("2025-02-01"),
                     "series_key": "a"}])
        with self.assertRaises(SystemExit):
            calibrate._split_fit_test(df)

    def test_fit_excludes_targets_on_or_after_test_origin(self):
        # Review fix (Finding 2): a FIT origin's own "12m" target window
        # can reach PAST test_origin (consecutive half_year_origins are
        # only 6 months apart, the window is 12) -- any such target
        # must never inform the correction, since it falls chrono-
        # logically inside (or after) the held-out TEST period.
        df = _rows([
            {"origin": pd.Timestamp("2025-01-01"), "series_key": "a",
             "target_date": pd.Timestamp("2025-03-01"), "y_true": 1.0},
            {"origin": pd.Timestamp("2025-01-01"), "series_key": "b",
             "target_date": pd.Timestamp("2025-09-01"), "y_true": 1.0},
            {"origin": pd.Timestamp("2025-07-01"), "series_key": "c",
             "target_date": pd.Timestamp("2025-09-01"), "y_true": 1.0},
        ])
        fit_origins, test_origin, fit_rows, test_rows = (
            calibrate._split_fit_test(df))
        self.assertEqual(fit_origins, [pd.Timestamp("2025-01-01")])
        self.assertEqual(test_origin, pd.Timestamp("2025-07-01"))
        self.assertEqual(list(fit_rows["series_key"]), ["a"])
        # TEST keeps ALL its own rows, never pruned -- even "c"'s target
        # date coincides with the one FIT excluded for "b".
        self.assertEqual(list(test_rows["series_key"]), ["c"])

    def test_raises_when_fit_is_empty_after_excluding_late_targets(self):
        df = _rows([
            {"origin": pd.Timestamp("2025-01-01"), "series_key": "a",
             "target_date": pd.Timestamp("2025-09-01"), "y_true": 1.0},
            {"origin": pd.Timestamp("2025-07-01"), "series_key": "b",
             "target_date": pd.Timestamp("2025-10-01"), "y_true": 1.0},
        ])
        with self.assertRaises(SystemExit):
            calibrate._split_fit_test(df)


if __name__ == "__main__":
    unittest.main()
