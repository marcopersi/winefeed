"""1.5: forecast.eval -- rolling-origin splitting (G1), metrics against
hand-computed values, and the two mandated tests (test_no_lookahead,
test_metric_known_values)."""
import math
import os
import sqlite3
import tempfile
import unittest

import numpy as np
import pandas as pd

import build_db
from forecast import data as fdata
from forecast import eval as feval
from forecast.models import QUANTILE_LEVELS, HORIZON_NEXT, HORIZON_12M


def _series(rows):
    """rows: list of (date_str, y, provider, qty) -> load_series-shaped
    DataFrame."""
    df = pd.DataFrame(rows, columns=["date", "y", "provider", "qty"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def _const_forecast(value=0.0):
    return {q: value for q in QUANTILE_LEVELS}


class HalfYearOriginsTest(unittest.TestCase):
    def test_boundaries_within_24_months(self):
        origins = feval.half_year_origins("2024-01-01")
        self.assertEqual(
            [o.strftime("%Y-%m-%d") for o in origins],
            ["2022-01-01", "2022-07-01", "2023-01-01", "2023-07-01",
             "2024-01-01"])

    def test_as_of_mid_year_still_hits_both_boundary_months(self):
        # start = 2022-09-15 -- the 2022 boundaries (01-01, 07-01) both
        # fall before it and are excluded; only the later four remain.
        origins = feval.half_year_origins("2024-09-15")
        self.assertEqual(
            [o.strftime("%Y-%m-%d") for o in origins],
            ["2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01"])


class AdmitsHorizonTest(unittest.TestCase):
    AS_OF = "2024-01-01"

    def test_next_admits_every_origin(self):
        self.assertTrue(
            feval.admits_horizon(pd.Timestamp("2023-07-01"), HORIZON_NEXT,
                                 self.AS_OF))
        self.assertTrue(
            feval.admits_horizon(pd.Timestamp("2024-01-01"), HORIZON_NEXT,
                                 self.AS_OF))

    def test_12m_excludes_a_right_censored_origin(self):
        # origin + 12m = 2024-01-01 == as_of -> just barely NOT censored
        self.assertTrue(
            feval.admits_horizon(pd.Timestamp("2023-01-01"), HORIZON_12M,
                                 self.AS_OF))
        # origin + 12m = 2024-07-01 > as_of -> censored, excluded
        self.assertFalse(
            feval.admits_horizon(pd.Timestamp("2023-07-01"), HORIZON_12M,
                                 self.AS_OF))


class SplitTest(unittest.TestCase):
    def test_boundary_date_on_origin_is_target_not_train(self):
        df = _series([
            ("2023-06-30", 1.0, "koppe", 1),
            ("2023-07-01", 2.0, "koppe", 1),
        ])
        train, targets = feval.split(df, pd.Timestamp("2023-07-01"),
                                     HORIZON_NEXT)
        self.assertEqual(len(train), 1)
        self.assertEqual(train["y"].iloc[0], 1.0)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets["y"].iloc[0], 2.0)

    def test_next_horizon_is_single_nearest_future_row(self):
        df = _series([
            ("2023-08-01", 1.0, "koppe", 1),
            ("2023-09-01", 2.0, "koppe", 1),
        ])
        _, targets = feval.split(df, pd.Timestamp("2023-07-01"),
                                 HORIZON_NEXT)
        self.assertEqual(len(targets), 1)
        self.assertEqual(targets["y"].iloc[0], 1.0)

    def test_12m_horizon_is_calendar_months_not_365_days(self):
        # origin=2023-03-01 -> calendar window [2023-03-01, 2024-03-01)
        # spans the 2024-02-29 leap day. A fixed 365-day window would
        # instead end at 2023-03-01+365d = 2024-02-29 (exclusive) --
        # one day short, wrongly excluding the 2024-02-29 row.
        df = _series([
            ("2024-02-28", 1.0, "koppe", 1),
            ("2024-02-29", 2.0, "koppe", 1),
            ("2024-03-01", 3.0, "koppe", 1),
        ])
        _, targets = feval.split(df, pd.Timestamp("2023-03-01"),
                                 HORIZON_12M)
        self.assertEqual(sorted(targets["y"]), [1.0, 2.0])


class DensityClassTest(unittest.TestCase):
    def test_buckets(self):
        self.assertEqual(feval.density_class(0), "0")
        self.assertEqual(feval.density_class(1), "1-2")
        self.assertEqual(feval.density_class(2), "1-2")
        self.assertEqual(feval.density_class(3), "3-4")
        self.assertEqual(feval.density_class(4), "3-4")
        self.assertEqual(feval.density_class(5), "5-9")
        self.assertEqual(feval.density_class(9), "5-9")
        self.assertEqual(feval.density_class(10), "10+")
        self.assertEqual(feval.density_class(500), "10+")


class ExtrapolationFlagTest(unittest.TestCase):
    def _train_with_last_y(self, last_y):
        return _series([("2023-01-01", last_y, "koppe", 1)])

    def test_within_bounds_is_not_flagged(self):
        train = self._train_with_last_y(0.0)
        forecast = _const_forecast(math.log(2.0))  # 2x -- within [0.2x, 5x]
        self.assertFalse(feval.extrapolation_flag(forecast, train))

    def test_outside_bounds_is_flagged(self):
        train = self._train_with_last_y(0.0)
        forecast = _const_forecast(math.log(10.0))  # 10x -- outside
        self.assertTrue(feval.extrapolation_flag(forecast, train))

    def test_empty_train_is_not_flagged(self):
        self.assertFalse(
            feval.extrapolation_flag(_const_forecast(0.0), train=self._train_with_last_y(0.0).iloc[0:0]))

    def test_extreme_forecast_does_not_overflow(self):
        # Confirmed real crash on the live DB: a "trend" baseline
        # extrapolated to a raw log-y forecast > ~709 (exp()'s double
        # overflow point), which math.exp()-ing (the first
        # implementation) raised OverflowError on -- this must instead
        # just come back flagged, same as any other out-of-bounds case.
        train = self._train_with_last_y(0.0)
        forecast = _const_forecast(1000.0)
        self.assertTrue(feval.extrapolation_flag(forecast, train))
        forecast_low = _const_forecast(-1000.0)
        self.assertTrue(feval.extrapolation_flag(forecast_low, train))


class ValidateForecastTest(unittest.TestCase):
    def test_rejects_missing_quantile(self):
        bad = {q: 0.0 for q in QUANTILE_LEVELS if q != 0.5}
        with self.assertRaises(ValueError):
            feval._validate_forecast(bad)

    def test_rejects_non_finite(self):
        bad = _const_forecast(0.0)
        bad[0.5] = float("nan")
        with self.assertRaises(ValueError):
            feval._validate_forecast(bad)

    def test_rejects_non_monotone(self):
        bad = _const_forecast(0.0)
        bad[0.9] = -1.0  # below q0.5=0.0 -- violates monotonicity
        with self.assertRaises(ValueError):
            feval._validate_forecast(bad)

    def test_accepts_constant_series_forecast(self):
        # 1.4 AC: "Konstante Serie => Prognose konstant, Intervallbreite
        # 0" -- all-equal quantiles must be valid (non-decreasing allows
        # equality, only a strict decrease is rejected).
        feval._validate_forecast(_const_forecast(1.23))


class NoLookaheadTest(unittest.TestCase):
    """G1's mandated test."""

    def test_train_never_contains_a_row_at_or_after_origin(self):
        df = _series([
            ("2022-02-01", 1.0, "koppe", 1),
            ("2022-08-01", 2.0, "koppe", 1),
            ("2023-02-01", 3.0, "koppe", 1),
            ("2023-08-01", 4.0, "koppe", 1),
        ])
        calls = []

        def spy(train, origin, horizon):
            if len(train):
                calls.append((origin, train["date"].max()))
            return _const_forecast(0.0)

        for horizon in (HORIZON_NEXT, HORIZON_12M):
            feval.evaluate_series(df, ("w", 2020, 7.5), spy, horizon,
                                  "2024-01-01", "spy")

        self.assertTrue(calls)
        for origin, train_max in calls:
            self.assertLess(train_max, origin)

    def test_cheating_capable_forecaster_cannot_see_the_future(self):
        # A forecaster that just averages whatever it's handed would
        # "cheat" and shift toward the future value IF the harness ever
        # let a future row leak into `train`. It never gets the chance
        # here, so its own average always equals the past-only value.
        past = math.log(100)
        future = math.log(1000)
        df = _series([
            ("2021-06-01", past, "koppe", 1),
            ("2023-06-01", future, "koppe", 1),
        ])
        medians = []

        def cheater(train, origin, horizon):
            if train.empty:
                return None
            m = float(train["y"].mean())
            return _const_forecast(m)

        for horizon in (HORIZON_NEXT, HORIZON_12M):
            rows, n_candidates, n_insufficient = feval.evaluate_series(
                df, ("w", 2020, 7.5), cheater, horizon, "2024-01-01",
                "cheater")
            self.assertGreater(n_candidates, 0)
            for row in rows:
                medians.append(row["q0.5"])

        self.assertTrue(medians)
        for m in medians:
            self.assertAlmostEqual(m, past, places=9)
            self.assertNotAlmostEqual(m, future, places=1)


class MetricKnownValuesTest(unittest.TestCase):
    """G1's other mandated test: every metric against hand-computed
    numbers, not just "doesn't crash"."""

    def setUp(self):
        # Same forecast for both rows: q0.025=-2, q0.1=-1, q0.25=-0.5,
        # q0.5=0, q0.75=0.5, q0.9=1, q0.975=2.
        forecast_cols = {
            "q0.025": -2.0, "q0.1": -1.0, "q0.25": -0.5, "q0.5": 0.0,
            "q0.75": 0.5, "q0.9": 1.0, "q0.975": 2.0,
        }
        # Row A sits exactly at the median (inside every interval).
        # Row B (y_true=3) is above every quantile bound (a miss ABOVE
        # every interval).
        rows = []
        for y_true in (0.0, 3.0):
            row = {"y_true": y_true, "density_class": "5-9",
                  "provider": "koppe", "extrapolation_flag": False}
            row.update(forecast_cols)
            rows.append(row)
        self.rows_df = pd.DataFrame(rows)

    def test_pinball_loss(self):
        self.assertAlmostEqual(
            feval.pinball_loss(self.rows_df, 0.1), 0.25, places=9)
        self.assertAlmostEqual(
            feval.pinball_loss(self.rows_df, 0.5), 0.75, places=9)
        self.assertAlmostEqual(
            feval.pinball_loss(self.rows_df, 0.9), 0.95, places=9)

    def test_winkler_score_and_coverage_and_width_per_level(self):
        # level 0.80 -> [q0.1, q0.9], alpha=0.20
        self.assertAlmostEqual(
            feval.winkler_score(self.rows_df, 0.80), 12.0, places=9)
        self.assertAlmostEqual(
            feval.coverage(self.rows_df, 0.80), 0.5, places=9)
        self.assertAlmostEqual(
            feval.median_width(self.rows_df, 0.80), 2.0, places=9)
        # level 0.50 -> [q0.25, q0.75], alpha=0.50
        self.assertAlmostEqual(
            feval.winkler_score(self.rows_df, 0.50), 6.0, places=9)
        self.assertAlmostEqual(
            feval.coverage(self.rows_df, 0.50), 0.5, places=9)
        self.assertAlmostEqual(
            feval.median_width(self.rows_df, 0.50), 1.0, places=9)
        # level 0.95 -> [q0.025, q0.975], alpha=0.05
        self.assertAlmostEqual(
            feval.winkler_score(self.rows_df, 0.95), 24.0, places=9)
        self.assertAlmostEqual(
            feval.coverage(self.rows_df, 0.95), 0.5, places=9)
        self.assertAlmostEqual(
            feval.median_width(self.rows_df, 0.95), 4.0, places=9)

    def test_mape_and_mdape_eur(self):
        # exp(0)=1 vs pred exp(0)=1 -> APE 0; exp(3)=e^3 vs pred 1.
        expected_ape_b = (math.exp(3.0) - 1.0) / math.exp(3.0)
        self.assertAlmostEqual(
            feval.mape_eur(self.rows_df), expected_ape_b / 2, places=9)
        self.assertAlmostEqual(
            feval.mdape_eur(self.rows_df), expected_ape_b / 2, places=9)

    def test_compute_metrics_matches_the_individual_functions(self):
        m = feval.compute_metrics(self.rows_df)
        self.assertEqual(m["n"], 2)
        self.assertAlmostEqual(m["pinball_q0.5"], 0.75, places=9)
        self.assertAlmostEqual(m["winkler_80"], 12.0, places=9)
        self.assertAlmostEqual(m["coverage_80"], 0.5, places=9)

    def test_compute_metrics_on_empty_frame_is_nan_not_a_crash(self):
        empty = self.rows_df.iloc[0:0]
        m = feval.compute_metrics(empty)
        self.assertEqual(m["n"], 0)
        self.assertTrue(math.isnan(m["mape_eur"]))
        self.assertEqual(m["n_extrapolation_excluded"], 0)

    def test_overflowing_forecast_is_excluded_from_mape_not_averaged_in(self):
        # Confirmed real crash/contamination on the live DB: a "trend"
        # baseline forecast whose exp() overflows must not turn the
        # whole group's MAPE into inf/an astronomical number -- it's
        # excluded and counted, not silently included or crashing.
        forecast_cols = {
            "q0.025": -2.0, "q0.1": -1.0, "q0.25": -0.5, "q0.5": 0.0,
            "q0.75": 0.5, "q0.9": 1.0, "q0.975": 2.0,
        }
        rows = []
        for y_true in (0.0, 2.0):  # two ordinary, finite rows
            row = {"y_true": y_true, "extrapolation_flag": False}
            row.update(forecast_cols)
            rows.append(row)
        overflow_row = {"y_true": 0.0, "extrapolation_flag": True}
        overflow_row.update({**forecast_cols, "q0.5": 1000.0})
        rows.append(overflow_row)
        df = pd.DataFrame(rows)

        ape = feval._eur_ape(df)
        self.assertEqual(feval.n_extrapolation_excluded(df), 1)
        mape = feval.mape_eur(df)
        self.assertFalse(math.isnan(mape))
        self.assertFalse(math.isinf(mape))
        # Matches the mean of ONLY the two finite, non-flagged rows.
        finite_ape = ape[~feval.extrapolation_exclusion_mask(df)]
        self.assertAlmostEqual(mape, float(finite_ape.mean()), places=9)
        m = feval.compute_metrics(df)
        self.assertEqual(m["n_extrapolation_excluded"], 1)
        self.assertEqual(m["n"], 3)  # the row count itself is untouched

    def test_finite_but_astronomical_forecast_is_also_excluded(self):
        # The gap this test closes: an even FIRST version of the fix
        # above filtered only ``np.isfinite`` -- which missed this
        # case entirely, since exp(600) is a perfectly finite double
        # (~3.77e260), not inf, yet still nowhere close to a real EUR
        # price. Confirmed on the live report: several groups' MAPE
        # stayed astronomical (e.g. "ackerwines": 2.8e50) even though
        # their own n_nonfinite count was 0 -- extrapolation_flag (not
        # isfinite alone) is what actually catches this.
        forecast_cols = {
            "q0.025": -2.0, "q0.1": -1.0, "q0.25": -0.5, "q0.5": 0.0,
            "q0.75": 0.5, "q0.9": 1.0, "q0.975": 2.0,
        }
        rows = []
        for y_true in (0.0, 2.0):
            row = {"y_true": y_true, "extrapolation_flag": False}
            row.update(forecast_cols)
            rows.append(row)
        huge_but_finite_row = {"y_true": 0.0, "extrapolation_flag": True}
        huge_but_finite_row.update({**forecast_cols, "q0.5": 600.0})
        rows.append(huge_but_finite_row)
        df = pd.DataFrame(rows)

        ape = feval._eur_ape(df)
        self.assertTrue(np.isfinite(ape[2]))  # finite, not inf -- the point
        self.assertEqual(feval.n_extrapolation_excluded(df), 1)
        mape = feval.mape_eur(df)
        self.assertLess(mape, 10.0)  # sane, not astronomical

    def test_extrapolation_exclusion_also_applies_to_pinball_winkler_coverage(self):
        # User decision (2026-11-10): the exclusion isn't MAPE-only --
        # confirmed on the live report, Pinball/Winkler for an
        # extrapolation-contaminated group stayed inflated (e.g.
        # "trend"/n_train=3-4: Pinball q0.5=1.23, Winkler 95%=78) even
        # after MAPE alone was fixed, just less visibly (log space
        # damps 1e50 to 78, doesn't remove it). This row's q0.5=1000 in
        # LOG SPACE directly inflates Pinball/Winkler/width without
        # needing exp() at all -- the exclusion must catch it too.
        sane_cols = {
            "q0.025": -2.0, "q0.1": -1.0, "q0.25": -0.5, "q0.5": 0.0,
            "q0.75": 0.5, "q0.9": 1.0, "q0.975": 2.0,
        }
        rows = []
        for y_true in (0.0, 0.5):
            row = {"y_true": y_true, "extrapolation_flag": False}
            row.update(sane_cols)
            rows.append(row)
        wild_row = {"y_true": 0.0, "extrapolation_flag": True,
                   "q0.025": -1000.0, "q0.1": -1000.0, "q0.25": -1000.0,
                   "q0.5": 1000.0, "q0.75": 1000.0, "q0.9": 1000.0,
                   "q0.975": 1000.0}
        rows.append(wild_row)
        df = pd.DataFrame(rows)

        self.assertEqual(feval.n_extrapolation_excluded(df), 1)
        for q in (0.1, 0.5, 0.9):
            self.assertLess(feval.pinball_loss(df, q), 10.0)
        for level in (0.50, 0.80, 0.95):
            self.assertLess(feval.winkler_score(df, level), 10.0)
            self.assertLess(feval.median_width(df, level), 10.0)
            self.assertGreaterEqual(feval.coverage(df, level), 0.0)

    def test_all_rows_excluded_is_nan_not_a_crash(self):
        row = {"y_true": 0.0, "extrapolation_flag": True}
        row.update({"q0.025": -2.0, "q0.1": -1.0, "q0.25": -0.5,
                    "q0.5": 0.0, "q0.75": 0.5, "q0.9": 1.0, "q0.975": 2.0})
        df = pd.DataFrame([row])
        self.assertTrue(math.isnan(feval.mape_eur(df)))
        self.assertTrue(math.isnan(feval.pinball_loss(df, 0.5)))
        self.assertTrue(math.isnan(feval.winkler_score(df, 0.80)))
        self.assertTrue(math.isnan(feval.coverage(df, 0.80)))
        self.assertTrue(math.isnan(feval.median_width(df, 0.80)))

    def test_summarize_splits_by_density_class_and_provider(self):
        rows = list(self.rows_df.to_dict("records"))
        rows[1] = dict(rows[1], density_class="10+", provider="christies")
        df = pd.DataFrame(rows)
        summary = feval.summarize(df)
        self.assertEqual(summary["overall"]["n"], 2)
        self.assertEqual(set(summary["by_density_class"]), {"5-9", "10+"})
        self.assertEqual(set(summary["by_provider"]), {"koppe", "christies"})
        self.assertEqual(summary["by_density_class"]["5-9"]["n"], 1)
        self.assertEqual(summary["by_provider"]["christies"]["n"], 1)


class EvaluateZeilenbilanzTest(unittest.TestCase):
    def test_candidates_equals_forecast_plus_insufficient(self):
        df = _series([
            ("2022-02-01", 1.0, "koppe", 1),
            ("2022-08-01", 2.0, "koppe", 1),
            ("2023-02-01", 3.0, "koppe", 1),
        ])

        def sometimes_insufficient(train, origin, horizon):
            if len(train) < 2:
                return None
            return _const_forecast(0.0)

        rows_df, tally = feval.evaluate(
            [(("w", 2020, 7.5), df)], sometimes_insufficient, HORIZON_NEXT,
            "2024-01-01", "sometimes")
        self.assertEqual(
            tally["n_forecast"] + tally["n_insufficient"],
            tally["n_candidates"])
        self.assertGreater(tally["n_candidates"], 0)
        self.assertEqual(len(rows_df), tally["n_forecast"])


class WriteBaselineReportSmokeTest(unittest.TestCase):
    """End-to-end wiring: load_all_series -> evaluate -> summarize ->
    Markdown file, with a trivial constant forecaster (1.4 adds real
    ones; this just proves the 1.5 scaffold runs without a model)."""

    def test_writes_a_report_with_zero_and_one_model(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        aid = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")
        import datetime
        recent = (datetime.date.today() - datetime.timedelta(days=10)
                 ).isoformat()
        lot_id = builder.add_lot(aid, {
            "lot_no": "1", "wine": "test-wine", "wine_ref_id": 1,
            "bottle_size_dl": 7.5, "quantity": 1, "lot_date": recent,
            "sold": 1, "hammer_price": 100.0})
        conn.execute(
            "UPDATE lots SET lot_kind='SINGLE', vintage_status='STRUCTURED',"
            " vintage_final=2015, price_per_bottle_eur=100.0 WHERE id=?",
            (lot_id,))

        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "report.md")
            feval.write_baseline_report(conn, {}, "2024-01-01", out)
            with open(out, encoding="utf-8") as f:
                empty_text = f.read()
            self.assertIn("Forecast Baseline Report", empty_text)

            feval.write_baseline_report(
                conn, {"constant": lambda train, o, h: _const_forecast(0.0)},
                "2024-01-01", out)
            with open(out, encoding="utf-8") as f:
                model_text = f.read()
            self.assertIn("constant", model_text)
            self.assertIn("Zeilenbilanz", model_text)
        conn.close()


if __name__ == "__main__":
    unittest.main()
