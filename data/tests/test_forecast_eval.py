"""1.5: forecast.eval -- rolling-origin splitting (G1), metrics against
hand-computed values, and the two mandated tests (test_no_lookahead,
test_metric_known_values)."""
# pylint: disable=protected-access
import math
import os
import sqlite3
import tempfile
import unittest

import numpy as np
import pandas as pd

import build_db
from forecast import eval as feval
from forecast.models import QUANTILE_LEVELS, HORIZON_NEXT, HORIZON_12M


def _series(rows):
    """rows: list of (date_str, y, provider, qty) -> load_series-shaped
    DataFrame, minus ``house_offset``/``lot_id`` (real ``load_series``
    has both; no test below combines this helper with
    ``origin_offsets``/``origin_outlier_ids``, which need them -- those
    build their DataFrame by hand instead, see e.g.
    ``OriginOutlierExclusionTest``)."""
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
        empty = self._train_with_last_y(0.0).iloc[0:0]
        self.assertFalse(
            feval.extrapolation_flag(_const_forecast(0.0), train=empty))

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

        def spy(train, origin, _horizon):
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

        def cheater(train, _origin, _horizon):
            if train.empty:
                return None
            m = float(train["y"].mean())
            return _const_forecast(m)

        for horizon in (HORIZON_NEXT, HORIZON_12M):
            rows, n_candidates, _n_insufficient = feval.evaluate_series(
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


class HouseOffsetInvarianceTest(unittest.TestCase):
    """Senior-review finding (D8): ``_eur_ape`` exponentiates
    ``y_true``, which is house-adjusted since D8 -- NOT the lot's real
    realised price in isolation. Verified numerically (not assumed)
    that every metric here is still correct regardless: a per-row
    constant offset cancels out of both a log-space difference
    (``a-b == (a+c)-(b+c)``, what Pinball/Winkler/coverage/width use)
    and a ratio/percentage error (``exp(a)/exp(b) ==
    exp(a+c)/exp(b+c)``, what MAPE/MdAPE reduce to). This test builds
    two rows with DIFFERENT simulated "house offsets" (not a uniform
    shift -- that would hide a mistake that only shows up when rows
    differ) and confirms every metric is identical whether or not that
    offset is present."""

    def _rows(self, offsets):
        forecast_cols = {
            "q0.025": -2.0, "q0.1": -1.0, "q0.25": -0.5, "q0.5": 0.0,
            "q0.75": 0.5, "q0.9": 1.0, "q0.975": 2.0,
        }
        rows = []
        for y_true, offset in zip((0.0, 3.0), offsets):
            row = {"y_true": y_true + offset, "extrapolation_flag": False}
            row.update({k: v + offset for k, v in forecast_cols.items()})
            rows.append(row)
        return pd.DataFrame(rows)

    def test_every_metric_is_unchanged_by_a_per_row_house_offset(self):
        unshifted = self._rows([0.0, 0.0])
        shifted = self._rows([0.5, -1.2])  # different offset per row
        self.assertAlmostEqual(
            feval.mape_eur(unshifted), feval.mape_eur(shifted), places=9)
        self.assertAlmostEqual(
            feval.mdape_eur(unshifted), feval.mdape_eur(shifted), places=9)
        for q in (0.1, 0.5, 0.9):
            self.assertAlmostEqual(
                feval.pinball_loss(unshifted, q),
                feval.pinball_loss(shifted, q), places=9)
        for level in (0.50, 0.80, 0.95):
            self.assertAlmostEqual(
                feval.winkler_score(unshifted, level),
                feval.winkler_score(shifted, level), places=9)
            self.assertAlmostEqual(
                feval.coverage(unshifted, level),
                feval.coverage(shifted, level), places=9)
            self.assertAlmostEqual(
                feval.median_width(unshifted, level),
                feval.median_width(shifted, level), places=9)


class ApplyOriginOffsetTest(unittest.TestCase):
    """G1 fix (Copilot review 2026-11-11, Finding 1):
    ``eval._apply_origin_offset`` undoes the full-data house offset
    already baked into ``y`` (``y + house_offset`` recovers the raw log
    price) and reapplies a point-in-time one instead."""

    def test_undoes_full_offset_and_reapplies_point_in_time(self):
        df = pd.DataFrame({
            "y": [1.0 - 0.4, 2.0 - 0.4],
            "house_offset": [0.4, 0.4],
            "provider": ["koppe", "langtons"],
        })
        corrected = feval._apply_origin_offset(
            df, {"koppe": 0.1, "langtons": 0.3})
        self.assertAlmostEqual(corrected["y"].iloc[0], 1.0 - 0.1, places=9)
        self.assertAlmostEqual(corrected["y"].iloc[1], 2.0 - 0.3, places=9)

    def test_missing_provider_gets_zero_offset(self):
        df = pd.DataFrame({"y": [1.0 - 0.4], "house_offset": [0.4],
                           "provider": ["unknown"]})
        corrected = feval._apply_origin_offset(df, {"koppe": 0.1})
        self.assertAlmostEqual(corrected["y"].iloc[0], 1.0, places=9)

    def test_none_offset_by_provider_is_a_no_op(self):
        # origin_offsets not supplied at all to evaluate_series -- the
        # pre-fix behaviour, for callers whose df was never house-
        # adjusted in the first place (e.g. every other test in this
        # file's synthetic fixtures).
        df = pd.DataFrame({"y": [0.6], "house_offset": [0.4],
                           "provider": ["koppe"]})
        corrected = feval._apply_origin_offset(df, None)
        self.assertIs(corrected, df)

    def test_empty_frame_is_a_no_op(self):
        df = pd.DataFrame({"y": [], "house_offset": [], "provider": []})
        corrected = feval._apply_origin_offset(df, {"koppe": 0.1})
        self.assertTrue(corrected.empty)


class OriginOffsetLeakageTest(unittest.TestCase):
    """G1 fix, Finding 1's own failure mode as a regression test:
    before this fix, EVERY origin's train/targets were adjusted with
    one single, full-data-fit offset, regardless of which origin was
    being scored -- i.e. partly informed by data that origin could not
    yet have seen. This confirms each origin now only ever sees ITS
    OWN entry in ``origin_offsets``, never a later origin's."""

    def test_each_origin_sees_only_its_own_point_in_time_offset(self):
        full_offset = 0.4  # the (buggy) full-data offset data.py bakes in
        df = pd.DataFrame({
            "date": pd.to_datetime(
                ["2021-06-01", "2022-02-01", "2022-08-01"]),
            "y": [1.0 - full_offset, 2.0 - full_offset, 3.0 - full_offset],
            "provider": ["koppe"] * 3,
            "qty": [1, 1, 1],
            "house_offset": [full_offset] * 3,
        })
        origin_offsets = {
            pd.Timestamp("2022-01-01"): {"koppe": 0.1},
            pd.Timestamp("2022-07-01"): {"koppe": 0.9},
        }
        seen_train_by_origin = {}

        def spy(train, origin, _horizon):
            if len(train):
                seen_train_by_origin.setdefault(origin, list(train["y"]))

        for horizon in (HORIZON_NEXT, HORIZON_12M):
            feval.evaluate_series(
                df, ("w", 2020, 7.5), spy, horizon, "2023-01-01", "spy",
                origin_offsets=origin_offsets)

        # Origin 2022-01-01's only training row is the raw-y=1.0 row --
        # corrected with THIS origin's own 0.1 offset, not the later
        # origin's 0.9, and not the un-corrected full_offset=0.4.
        self.assertAlmostEqual(
            seen_train_by_origin[pd.Timestamp("2022-01-01")][0],
            1.0 - 0.1, places=9)
        # Origin 2022-07-01's training includes the raw-y=2.0 row,
        # corrected with 0.9 -- never 0.1, never 0.4.
        self.assertAlmostEqual(
            seen_train_by_origin[pd.Timestamp("2022-07-01")][-1],
            2.0 - 0.9, places=9)


class IsActiveAsOfTest(unittest.TestCase):
    """G1 fix (Copilot review 2026-11-11, Finding B part 1):
    ``eval._is_active_as_of`` recomputes D15's recency check relative
    to an origin instead of "now"."""

    def test_empty_train_is_not_active(self):
        df = _series([])
        self.assertFalse(feval._is_active_as_of(df, pd.Timestamp("2022-01-01")))

    def test_recent_train_is_active(self):
        df = _series([("2021-10-01", 1.0, "koppe", 1)])
        self.assertTrue(
            feval._is_active_as_of(df, pd.Timestamp("2022-01-01")))

    def test_stale_train_is_not_active(self):
        # Last pre-origin row is 37 months before the origin -- just
        # past the 36-month D15 threshold.
        df = _series([("2018-12-01", 1.0, "koppe", 1)])
        self.assertFalse(
            feval._is_active_as_of(df, pd.Timestamp("2022-01-01")))

    def test_exactly_36_months_is_still_active(self):
        df = _series([("2019-01-01", 1.0, "koppe", 1)])
        self.assertTrue(
            feval._is_active_as_of(df, pd.Timestamp("2022-01-01")))


class ExcludeOutlierRowsTest(unittest.TestCase):
    """G1 fix (Copilot review 2026-11-11, Finding B part 2):
    ``eval._exclude_outlier_rows`` drops rows by ``lot_id``, scoped to
    whatever ``outlier_lot_ids`` the caller passes for ONE origin."""

    def test_drops_only_the_listed_lot_ids(self):
        df = pd.DataFrame({"lot_id": [10, 20, 30], "y": [1.0, 2.0, 3.0]})
        out = feval._exclude_outlier_rows(df, {20})
        self.assertEqual(list(out["lot_id"]), [10, 30])

    def test_empty_outlier_set_is_a_no_op(self):
        df = pd.DataFrame({"lot_id": [10], "y": [1.0]})
        out = feval._exclude_outlier_rows(df, set())
        self.assertIs(out, df)

    def test_empty_frame_is_a_no_op(self):
        df = pd.DataFrame({"lot_id": [], "y": []})
        out = feval._exclude_outlier_rows(df, {10})
        self.assertIs(out, df)


class RecencyEligibilityLeakageTest(unittest.TestCase):
    """G1 fix, Finding B part 1's own failure mode as a regression
    test: a series that went quiet, then revived long after, must not
    be scored at an EARLY origin where it had already been dormant for
    over 36 months -- that origin is skipped entirely (not counted),
    the same treatment a globally-dormant series already gets (it
    simply never appears in ``df`` for ANY origin)."""

    def test_early_origin_skipped_until_the_series_reactivates(self):
        df = _series([
            ("2017-01-01", 1.0, "koppe", 1),   # dormant era
            ("2022-02-01", 2.0, "koppe", 1),   # reactivation
            ("2022-09-01", 3.0, "koppe", 1),   # first post-reactivation sale
        ])
        seen = []

        def spy(train, origin, _horizon):
            seen.append((origin, list(train["y"])))

        feval.evaluate_series(
            df, ("w", 2020, 7.5), spy, HORIZON_NEXT, "2023-07-01", "spy")

        # Only one origin ever reaches the forecaster: 2022-07-01 (train
        # = the dormant row + the reactivation row, target = the row
        # after). The two origins before reactivation (2021-07-01,
        # 2022-01-01) see only the >36-months-stale dormant row and are
        # skipped; the two after (2023-01-01, 2023-07-01) have no target
        # row left (both skipped for that unrelated, pre-existing
        # reason).
        self.assertEqual(len(seen), 1)
        origin, train_y = seen[0]
        self.assertEqual(origin, pd.Timestamp("2022-07-01"))
        self.assertEqual(train_y, [1.0, 2.0])


class OriginOutlierExclusionTest(unittest.TestCase):
    """G1 fix, Finding B part 2's own failure mode as a regression
    test: ``origin_outlier_ids`` excludes a training row for exactly
    the origin it was computed for, never a different one."""

    def test_excludes_the_flagged_lot_only_for_its_own_origin(self):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2021-06-01", "2022-02-01", "2022-09-01"]),
            "y": [1.0, 2.0, 3.0],
            "provider": ["koppe"] * 3,
            "qty": [1, 1, 1],
            "lot_id": [111, 222, 333],
        })
        origin_outlier_ids = {
            pd.Timestamp("2022-01-01"): {111},
            pd.Timestamp("2022-07-01"): set(),
        }
        seen_train_by_origin = {}

        def spy(train, origin, _horizon):
            seen_train_by_origin[origin] = list(train["lot_id"])

        feval.evaluate_series(
            df, ("w", 2020, 7.5), spy, HORIZON_NEXT, "2023-01-01", "spy",
            origin_outlier_ids=origin_outlier_ids)

        # Origin 2022-01-01: lot 111 is flagged for THIS origin -> excluded.
        self.assertEqual(
            seen_train_by_origin[pd.Timestamp("2022-01-01")], [])
        # Origin 2022-07-01: lot 111 is NOT flagged for this later
        # origin (empty set) -> still present, never the other origin's
        # exclusion leaking across.
        self.assertEqual(
            seen_train_by_origin[pd.Timestamp("2022-07-01")], [111, 222])


class OriginOutlierLotIdsTest(unittest.TestCase):
    """G1 fix (Copilot review 2026-11-11, Finding B part 2):
    ``eval._origin_outlier_lot_ids`` must recompute the median/MAD test
    from ONLY pre-origin data -- reusing the exact fixture shape
    already proven (in test_loader_roundtrip.py) to flag exactly one
    lot (5 normal prices + 1 extreme 9000.0), then adding enough
    POST-origin 9000.0 rows to the SAME group that a FULL-history
    recompute would flip the verdict: the original pre-origin outlier
    stops looking extreme once it is just one more member of a
    now-dominant 9000.0 cluster. ``_origin_outlier_lot_ids`` must still
    flag it -- a real point-in-time system could not have known about
    those future sales."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(build_db.SCHEMA)
        self.builder = build_db.Builder(self.conn)
        self.aid = self.builder.add_auction(
            "koppe", "1", "x", None, "EUR", "HAMMER")
        self._n = 0

    def tearDown(self):
        self.conn.close()

    def _lot(self, price, lot_date):
        self._n += 1
        lot_id = self.builder.add_lot(self.aid, {
            "lot_no": str(self._n), "wine": "w", "vintage": 2017,
            "wine_ref_id": 3, "lot_date": lot_date})
        self.conn.execute(
            "UPDATE lots SET price_per_bottle_eur=?, lot_kind='SINGLE',"
            " vintage_status='STRUCTURED', vintage_final=2017 WHERE id=?",
            (price, lot_id))
        return lot_id

    def test_pre_origin_outlier_still_flagged_despite_later_data(self):
        origin = "2022-01-01"
        pre_origin_date = "2021-06-01"
        normal_ids = [self._lot(40.0 + i, pre_origin_date) for i in range(5)]
        extreme_id = self._lot(9000.0, pre_origin_date)

        # 20 post-origin sales clustered near the same extreme price --
        # enough to dominate a full-history median/MAD for this group.
        # Slightly different prices (9000..9019), not 20 IDENTICAL
        # ones: an exactly-identical majority would make the new
        # cluster's own MAD exactly 0, which _outlier_lot_ids skips
        # entirely (nothing to measure against) -- that would prove
        # nothing about this fix, just hit an unrelated guard.
        for i in range(20):
            self._lot(9000.0 + i, "2023-06-01")

        # Sanity check: the FULL-history recompute (the already-shipped
        # build_db._flag_price_outliers) now flags the 5 ORIGINAL
        # "normal" lots instead, not the original extreme one -- proof
        # this fixture really does flip the verdict, not just add noise.
        build_db._flag_price_outliers(self.conn)
        full_history_flagged = {
            row[0] for row in self.conn.execute(
                "SELECT id FROM lots WHERE instr(COALESCE(ppb_flags,''),"
                " 'OUTLIER') > 0")}
        self.assertTrue(full_history_flagged & set(normal_ids))
        self.assertNotIn(extreme_id, full_history_flagged)

        origin_flagged = feval._origin_outlier_lot_ids(self.conn, origin)
        self.assertEqual(origin_flagged, {extreme_id})


class PairedComparisonTest(unittest.TestCase):
    """Copilot review, Finding 3 (Low): ``eval.paired_comparison``
    restricts every model's rows to the target lots EVERY model in the
    comparison actually scored."""

    def _row(self, series_key, origin, horizon, target_date, q05,
            extrapolation_flag=False):
        return {
            "series_key": series_key, "origin": origin, "horizon": horizon,
            "target_date": target_date, "y_true": 0.0,
            "extrapolation_flag": extrapolation_flag,
            "q0.025": q05 - 2, "q0.1": q05 - 1, "q0.25": q05 - 0.5,
            "q0.5": q05, "q0.75": q05 + 0.5, "q0.9": q05 + 1,
            "q0.975": q05 + 2,
        }

    def test_restricts_to_the_common_key_intersection(self):
        common_key = ("w", pd.Timestamp("2022-01-01"), HORIZON_NEXT,
                     pd.Timestamp("2022-02-01"))
        only_a_key = ("w", pd.Timestamp("2022-07-01"), HORIZON_NEXT,
                     pd.Timestamp("2022-08-01"))
        rows_a = pd.DataFrame([
            self._row(*common_key, q05=0.0),
            self._row(*only_a_key, q05=5.0),
        ])
        rows_b = pd.DataFrame([self._row(*common_key, q05=1.0)])

        result = feval.paired_comparison({"a": rows_a, "b": rows_b})
        self.assertEqual(result["a"]["n_own"], 2)
        self.assertEqual(result["a"]["n_paired"], 1)
        self.assertEqual(result["b"]["n_own"], 1)
        self.assertEqual(result["b"]["n_paired"], 1)
        self.assertAlmostEqual(
            result["a"]["pinball_q0.5_paired"],
            feval.pinball_loss(rows_a.iloc[[0]], 0.5), places=9)
        self.assertAlmostEqual(
            result["b"]["pinball_q0.5_paired"],
            feval.pinball_loss(rows_b, 0.5), places=9)

    def test_empty_input_is_an_empty_dict(self):
        self.assertEqual(feval.paired_comparison({}), {})

    def test_model_specific_exclusion_is_applied_before_pairing(self):
        # Copilot review, Finding A (Medium, 2026-11-11): intersecting
        # RAW keys before each model's own extrapolation_exclusion_mask
        # could report the same n_paired for two models whose PAIRED
        # pinball average is in fact computed over different rows --
        # here, model "a" flags the shared key as EXTRAPOLATION (so its
        # own pinball_loss would silently drop it), model "b" does not.
        shared_key = ("w", pd.Timestamp("2022-01-01"), HORIZON_NEXT,
                     pd.Timestamp("2022-02-01"))
        other_key = ("w", pd.Timestamp("2022-07-01"), HORIZON_NEXT,
                    pd.Timestamp("2022-08-01"))
        rows_a = pd.DataFrame([
            self._row(*shared_key, q05=0.0, extrapolation_flag=True),
            self._row(*other_key, q05=1.0),
        ])
        rows_b = pd.DataFrame([
            self._row(*shared_key, q05=2.0, extrapolation_flag=False),
            self._row(*other_key, q05=3.0),
        ])

        result = feval.paired_comparison({"a": rows_a, "b": rows_b})

        # The flagged shared_key must not count for EITHER model, even
        # though model "b" never flagged it itself -- a true pairing
        # needs every model to have actually SCORED a target, not just
        # attempted it.
        self.assertEqual(result["a"]["n_paired"], 1)
        self.assertEqual(result["b"]["n_paired"], 1)
        self.assertAlmostEqual(
            result["a"]["pinball_q0.5_paired"],
            feval.pinball_loss(rows_a.iloc[[1]], 0.5), places=9)
        self.assertAlmostEqual(
            result["b"]["pinball_q0.5_paired"],
            feval.pinball_loss(rows_b.iloc[[1]], 0.5), places=9)


class WriteBaselineReportPairedSectionTest(unittest.TestCase):
    def test_paired_section_and_return_value_with_two_models(self):
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
        try:
            with tempfile.TemporaryDirectory() as d:
                out = os.path.join(d, "report.md")
                forecasters = {
                    "a": lambda train, o, h: _const_forecast(0.0),
                    "b": lambda train, o, h: _const_forecast(0.1),
                }
                rows = feval.write_baseline_report(
                    conn, forecasters, "2024-01-01", out)
                with open(out, encoding="utf-8") as f:
                    text = f.read()
            self.assertIn("Paired-Vergleich", text)
            self.assertEqual(
                set(rows),
                {("a", HORIZON_NEXT), ("a", HORIZON_12M),
                 ("b", HORIZON_NEXT), ("b", HORIZON_12M)})
        finally:
            conn.close()


class EvaluateZeilenbilanzTest(unittest.TestCase):
    def test_candidates_equals_forecast_plus_insufficient(self):
        df = _series([
            ("2022-02-01", 1.0, "koppe", 1),
            ("2022-08-01", 2.0, "koppe", 1),
            ("2023-02-01", 3.0, "koppe", 1),
        ])

        def sometimes_insufficient(train, _origin, _horizon):
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
