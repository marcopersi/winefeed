"""forecast.calibrate -- Stufe 4.1 (Split-Conformal) als reine
Funktionen ueber einem synthetischen ``eval.evaluate``-Rueckgabe-
DataFrame, keine DB noetig (dieselbe Shape wie eval.py's echte
Pro-Ziel-Zeilen: ``origin``, ``density_class``, ``y_true``, ``q0.5``,
...)."""
import unittest

import pandas as pd

from forecast import calibrate


def _rows(records):
    return pd.DataFrame(records)


class FitTableTests(unittest.TestCase):
    def test_correction_is_quantile_of_absolute_residual(self):
        # density_class "3-4": residuals |y_true - q0.5| = 0, 0.2, 0.4, 0.6, 0.8
        df = _rows([
            {"density_class": "3-4", "y_true": 1.0 + d, "q0.5": 1.0}
            for d in (0.0, 0.2, 0.4, 0.6, 0.8)
        ])
        table = calibrate.fit_table(df)
        # pandas' default (linear) quantile of [0,.2,.4,.6,.8] at 0.5 is 0.4.
        self.assertAlmostEqual(table["3-4"]["0.5"], 0.4)

    def test_pooled_fallback_used_for_class_missing_from_fit_split(self):
        df = _rows([
            {"density_class": "10+", "y_true": 1.0, "q0.5": 1.0},
            {"density_class": "10+", "y_true": 1.5, "q0.5": 1.0},
        ])
        table = calibrate.fit_table(df)
        # falls back to the pooled ("_pooled") correction, not a KeyError.
        self.assertEqual(
            calibrate._correction(table, "1-2", 0.5),
            table["_pooled"]["0.5"])

    def test_every_known_density_class_has_an_entry(self):
        # Review fix: a future Stage-5 reader indexes calibration_table.json
        # directly (table[dclass]), so every eval._DENSITY_BINS label (plus
        # "10+") must be present even when absent from THIS fit split.
        df = _rows([{"density_class": "10+", "y_true": 1.0, "q0.5": 1.0}])
        table = calibrate.fit_table(df)
        for dclass in calibrate._KNOWN_DENSITY_CLASSES:
            self.assertIn(dclass, table)
        self.assertEqual(table["1-2"], table["_pooled"])


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
        df = _rows([{"origin": pd.Timestamp("2025-01-01"), "y_true": 1.0}])
        with self.assertRaises(SystemExit):
            calibrate._split_fit_test(df)

    def test_drops_test_row_whose_target_already_scored_in_fit(self):
        # Review fix (Finding 1): eval.split's target windows for
        # consecutive origins overlap, so the SAME realised observation
        # (series_key, target_date) can be a scored target row under
        # both the FIT origin and the TEST origin -- that row must not
        # count as "held-out" evidence.
        shared_target = pd.Timestamp("2025-09-01")
        df = _rows([
            {"origin": pd.Timestamp("2025-01-01"), "series_key": "shared",
             "target_date": shared_target, "y_true": 1.0},
            {"origin": pd.Timestamp("2025-07-01"), "series_key": "shared",
             "target_date": shared_target, "y_true": 1.0},
            {"origin": pd.Timestamp("2025-07-01"), "series_key": "other",
             "target_date": pd.Timestamp("2025-10-01"), "y_true": 1.0},
        ])
        _, _, fit_rows, test_rows = calibrate._split_fit_test(df)
        self.assertEqual(len(fit_rows), 1)
        self.assertEqual(list(test_rows["series_key"]), ["other"])


class DropOverlappingTargetsTests(unittest.TestCase):
    def test_keeps_only_targets_absent_from_fit(self):
        fit_rows = _rows([
            {"series_key": "a", "target_date": pd.Timestamp("2025-01-01")},
        ])
        test_rows = _rows([
            {"series_key": "a", "target_date": pd.Timestamp("2025-01-01")},
            {"series_key": "a", "target_date": pd.Timestamp("2025-02-01")},
            {"series_key": "b", "target_date": pd.Timestamp("2025-01-01")},
        ])
        kept = calibrate._drop_overlapping_targets(fit_rows, test_rows)
        self.assertEqual(len(kept), 2)
        self.assertNotIn(
            ("a", pd.Timestamp("2025-01-01")),
            set(zip(kept["series_key"], kept["target_date"])))


if __name__ == "__main__":
    unittest.main()
