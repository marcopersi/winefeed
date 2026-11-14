"""2.1-2.6: forecast.models.local_level_forecast/local_linear_trend_forecast
-- _LocalLevelTrend (level, optional damped slope) on a monthly-aggregated
grid with per-month observation-variance weighting, their prediction-
interval quantiles, and the FIT_FAILED variance-floor/convergence guards.
"""
# pylint: disable=protected-access
import unittest
import unittest.mock

import numpy as np
import pandas as pd

from forecast import models
from forecast.models import HORIZON_NEXT, HORIZON_12M, QUANTILE_LEVELS


def _series(rows):
    df = pd.DataFrame(rows, columns=["date", "y", "provider", "qty"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def _level_path(n, sigma_eta, rng):
    """A random-walk level path: ``n`` steps, innovation SD ``sigma_eta``,
    drawn from ``rng`` -- the shared level-generation step
    ``_random_walk_series``/``_multi_lot_series`` both build on, so a
    future change to the level-path model only needs editing once."""
    return np.cumsum(rng.normal(0, sigma_eta, n))


def _random_walk_series(n, sigma_eta, sigma_eps, seed, freq="MS",
                        start="2000-01-01"):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=n, freq=freq)
    level = _level_path(n, sigma_eta, rng)
    y = level + rng.normal(0, sigma_eps, n)
    return _series([(d.isoformat(), float(v), "koppe", 1)
                    for d, v in zip(dates, y)])


def _multi_lot_series(n, k, sigma_eta, sigma_eps, seed, start="2000-01-01"):
    """``n`` calendar months, ``k`` lots each, level drift ``sigma_eta``
    and per-lot observation noise ``sigma_eps`` -- the shape where
    monthly aggregation discards real within-month scatter."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=n, freq="MS")
    level = _level_path(n, sigma_eta, rng)
    rows = []
    for i, d in enumerate(dates):
        for _ in range(k):
            rows.append((d.isoformat(),
                         float(level[i] + rng.normal(0, sigma_eps)),
                         "koppe", 1))
    return _series(rows)


class MonthlySeriesTest(unittest.TestCase):
    def test_aggregates_to_calendar_month_mean(self):
        df = _series([
            ("2020-01-05", 1.0, "koppe", 1),
            ("2020-01-20", 3.0, "koppe", 1),
            ("2020-03-10", 5.0, "koppe", 1),
        ])
        monthly = models._monthly_series(df)
        self.assertEqual(
            [d.strftime("%Y-%m-%d") for d in monthly.index],
            ["2020-01-01", "2020-02-01", "2020-03-01"])
        self.assertAlmostEqual(monthly.iloc[0], 2.0)  # mean(1.0, 3.0)
        self.assertTrue(np.isnan(monthly.iloc[1]))  # no lots in Feb
        self.assertAlmostEqual(monthly.iloc[2], 5.0)


class MonthlyWeightsTest(unittest.TestCase):
    def test_counts_lots_per_month_aligned_to_monthly_series(self):
        df = _series([
            ("2020-01-05", 1.0, "koppe", 1),
            ("2020-01-20", 3.0, "koppe", 1),
            ("2020-01-25", 4.0, "koppe", 1),
            ("2020-03-10", 5.0, "koppe", 1),
        ])
        monthly = models._monthly_series(df)
        weights = models._monthly_weights(df)
        self.assertEqual(len(weights), len(monthly))
        self.assertEqual(list(weights), [3.0, 1.0, 1.0])  # Feb: placeholder


class MonthsBetweenTest(unittest.TestCase):
    def test_counts_calendar_months_not_days(self):
        self.assertEqual(
            models._months_between("2023-01-01", "2023-07-01"), 6)
        self.assertEqual(
            models._months_between("2023-12-01", "2024-01-01"), 1)
        self.assertEqual(
            models._months_between("2023-01-15", "2023-02-01"), 1)


class LocalLevelTrendRecoversKnownVarianceTest(unittest.TestCase):
    def test_sigma2_estimates_within_30_percent(self):
        # Fixed seed (G5), >= 200 months -- a short series won't recover
        # within 30% (MLE sampling noise dominates). One lot per month
        # (weights all 1) isolates this from the weighting mechanism,
        # same synthetic shape 2.2's original test used.
        sigma_eta, sigma_eps = 0.08, 0.15
        df = _random_walk_series(240, sigma_eta, sigma_eps, seed=0)
        monthly = models._monthly_series(df)
        weights = models._monthly_weights(df)
        mod = models._LocalLevelTrend(monthly, weights, trend=False)
        res = mod.fit(disp=False)
        self.assertTrue(res.mle_retvals.get("converged"))
        est_eta = res.params["sigma2.level"] ** 0.5
        est_eps = res.params["sigma2.irregular"] ** 0.5
        self.assertAlmostEqual(est_eta / sigma_eta, 1.0, delta=0.3)
        self.assertAlmostEqual(est_eps / sigma_eps, 1.0, delta=0.3)


class PerMonthWeightingTest(unittest.TestCase):
    """2.1/2.6 fix (2026-11-13): sigma2.irregular is divided by each
    month's own lot count k_t, replacing the additive within-month-
    variance correction this model used to need -- confirm the weight
    actually changes the fitted sigma2.irregular, not just that it's
    accepted without error."""

    def test_weighting_changes_the_fitted_irregular_variance(self):
        rng = np.random.default_rng(7)
        n = 120
        weights = rng.integers(1, 10, n).astype(float)
        true_level = np.cumsum(rng.normal(0, 0.005 ** 0.5, n))
        y = true_level + rng.normal(0, (0.25 / weights) ** 0.5, n)
        idx = pd.date_range("2010-01-01", periods=n, freq="MS")
        monthly = pd.Series(y, index=idx)

        res_weighted = models._LocalLevelTrend(
            monthly, weights, trend=False).fit(disp=False)
        res_unweighted = models._LocalLevelTrend(
            monthly, np.ones(n), trend=False).fit(disp=False)

        diff = abs(res_weighted.params["sigma2.irregular"]
                   - res_unweighted.params["sigma2.irregular"])
        self.assertGreater(diff, 0.01)

    def test_zero_lot_months_get_a_placeholder_weight_not_a_crash(self):
        df = _series([
            ("2020-01-05", 1.0, "koppe", 1),
            ("2020-03-10", 5.0, "koppe", 1),
        ])
        monthly = models._monthly_series(df)
        weights = models._monthly_weights(df)
        mod = models._LocalLevelTrend(monthly, weights, trend=False)
        res = mod.fit(disp=False)
        self.assertTrue(np.isfinite(res.llf))


class WithinMonthScatterTest(unittest.TestCase):
    """2.1/2.6 follow-up (Copilot review, 2026-11-14): fitting only
    monthly means and counts discards the within-month lot scatter,
    letting ``sigma2.irregular`` collapse to its floor whenever a
    drifting level plus several lots per month make the means alone
    tight. The within-month SSE is now re-added to the likelihood."""

    def test_sigma2_irregular_recovers_per_lot_noise_with_multi_lot_months(
            self):
        # 5 lots/month, per-lot SD 0.3 (variance 0.09), strong level
        # drift (0.4/month): the monthly means alone drive
        # sigma2.irregular below its 0.01 floor, so the within-month
        # scatter must be what recovers it.
        df = _multi_lot_series(60, 5, sigma_eta=0.4, sigma_eps=0.3, seed=42)
        monthly = models._monthly_series(df)
        weights = models._monthly_weights(df)
        within_positions, within_sse, within_df = (
            models._monthly_within_scatter(df, monthly.index))
        mod = models._LocalLevelTrend(
            monthly, weights, trend=False, within_sse=within_sse,
            within_df=within_df, within_positions=within_positions)
        res = mod.fit(disp=False)
        self.assertTrue(res.mle_retvals.get("converged"))
        est = float(res.params["sigma2.irregular"])
        self.assertAlmostEqual(est / 0.09, 1.0, delta=0.3)

    def test_loglike_equals_sum_of_loglikeobs_with_within_month_scatter(
            self):
        # Code-review finding, 2026-11-14: an earlier version only
        # overrode loglike(), silently breaking the loglike() ==
        # sum(loglikeobs()) identity statsmodels' OPG covariance
        # (bse/pvalues/.summary()) and aic/bic rely on.
        df = _multi_lot_series(60, 5, sigma_eta=0.4, sigma_eps=0.3, seed=42)
        monthly = models._monthly_series(df)
        weights = models._monthly_weights(df)
        within_positions, within_sse, within_df = (
            models._monthly_within_scatter(df, monthly.index))
        self.assertGreater(len(within_df), 0)  # the correction is live
        mod = models._LocalLevelTrend(
            monthly, weights, trend=False, within_sse=within_sse,
            within_df=within_df, within_positions=within_positions)
        params = mod.transform_params(mod.start_params)
        llf = mod.loglike(params, transformed=True)
        llf_sum = float(np.sum(mod.loglikeobs(params, transformed=True)))
        self.assertAlmostEqual(llf, llf_sum, places=9)

    def test_full_forecast_path_does_not_floor_sigma2_irregular(self):
        # Same scenario through the real local_level_forecast entry
        # point, checking the wiring actually forwards the within-month
        # scatter: before the fix, this exact shape hit the 0.01 floor
        # and clamped sigma2.irregular.
        df = _multi_lot_series(60, 5, sigma_eta=0.4, sigma_eps=0.3, seed=42)
        origin = (pd.Timestamp(df["date"].iloc[-1].year,
                               df["date"].iloc[-1].month, 1)
                  + pd.DateOffset(months=1))
        result = models.local_level_forecast(df, origin, HORIZON_NEXT)
        self.assertNotEqual(result, "FIT_FAILED")
        self.assertIsNotNone(result)
        _quantiles, clamped = result
        self.assertFalse(clamped["sigma2.irregular"])

    def test_full_forecast_path_does_not_floor_sigma2_irregular_trend(self):
        # Same wiring check as above, through local_linear_trend_forecast
        # (trend=True) -- both share _llt_forecast, but nothing
        # previously confirmed the within-month-scatter forwarding
        # survives that path too (code-review finding, 2026-11-14).
        df = _multi_lot_series(60, 5, sigma_eta=0.4, sigma_eps=0.3, seed=42)
        origin = (pd.Timestamp(df["date"].iloc[-1].year,
                               df["date"].iloc[-1].month, 1)
                  + pd.DateOffset(months=1))
        result = models.local_linear_trend_forecast(df, origin, HORIZON_NEXT)
        self.assertNotEqual(result, "FIT_FAILED")
        self.assertIsNotNone(result)
        _quantiles, clamped = result
        self.assertFalse(clamped["sigma2.irregular"])


class PredictionIntervalIncludesMeasurementNoiseTest(unittest.TestCase):
    def test_forecast_variance_is_at_least_the_per_lot_observation_noise(
            self):
        # 2.4's own mandated test: "Prädiktions- nicht Konfidenz-
        # intervall (Messrauschen einrechnen!)". One lot per month
        # (weights all 1), so sigma2.irregular directly IS the per-lot
        # noise variance the forecast must include at minimum.
        df = _random_walk_series(200, sigma_eta=0.0, sigma_eps=0.2, seed=1)
        monthly = models._monthly_series(df)
        weights = models._monthly_weights(df)
        mod = models._LocalLevelTrend(monthly, weights, trend=False)
        res = mod.fit(disp=False)
        sigma2_irregular = res.params["sigma2.irregular"]
        for h in (1, 6, 24):
            var = res.get_forecast(h).var_pred_mean.iloc[-1]
            self.assertGreaterEqual(var, sigma2_irregular)

    def test_forecast_variance_equals_state_variance_plus_full_noise(self):
        # Fixed-parameter case with training weights greater than 1
        # (Copilot review, 2026-11-14): the forecast scores ONE
        # individual lot, so its variance must be the propagated state
        # variance plus the FULL sigma2.irregular -- not sigma2.irregular
        # / k_t, which a clone() mistakenly reusing a training weight > 1
        # would return. sigma2.level=0 leaves the level exactly known,
        # so the state variance is ~0 and the forecast variance collapses
        # to the full sigma2.irregular.
        sigma2_irregular = 0.25
        df = _multi_lot_series(120, 5, sigma_eta=0.0,
                               sigma_eps=sigma2_irregular ** 0.5, seed=11)
        monthly = models._monthly_series(df)
        weights = models._monthly_weights(df)
        mod = models._LocalLevelTrend(monthly, weights, trend=False)
        res = mod.smooth(np.array([sigma2_irregular, 0.0]))
        var = float(res.get_forecast(1).var_pred_mean.iloc[-1])
        self.assertAlmostEqual(var, sigma2_irregular, places=2)


class LocalLevelForecastTest(unittest.TestCase):
    def _origin_after(self, df):
        last = df["date"].iloc[-1]
        return pd.Timestamp(last.year, last.month, 1) + pd.DateOffset(
            months=1)

    def test_too_few_months_returns_none(self):
        df = _series([("2020-01-15", 1.0, "koppe", 1)])
        origin = self._origin_after(df)
        self.assertIsNone(
            models.local_level_forecast(df, origin, HORIZON_NEXT))

    def test_exactly_constant_series_does_not_converge_is_fit_failed(self):
        # Confirmed empirically, not assumed: an EXACTLY flat series
        # (every y identical) makes the MLE optimizer itself fail to
        # converge (mle_retvals["converged"] is False) -- a real
        # non-convergence, the one case _SIGMA2_FLOORS' own docstring
        # says still gets FIT_FAILED, not clamped. A real auction
        # series is never this exact, so this only matters for a
        # synthetic edge case like this one.
        dates = pd.date_range("2018-01-01", periods=24, freq="MS")
        df = _series([(d.isoformat(), 5.0, "koppe", 1) for d in dates])
        origin = self._origin_after(df)
        self.assertEqual(
            models.local_level_forecast(df, origin, HORIZON_NEXT),
            "FIT_FAILED")

    def test_near_zero_observation_noise_is_clamped_not_failed(self):
        # Senior-review finding (confirmed on a 400-series live-DB
        # sample): strong level drift with near-zero observation noise
        # is COMMON for this model with one observation per month (the
        # two variance components are weakly identified) -- the fitted
        # sigma2.irregular collapses below the floor but the fit itself
        # converges fine. This must clamp and still return a forecast,
        # not FIT_FAILED (the original, wrong reading of "Untergrenzen
        # für sigma^2" as a rejection rule rejected ~50% of all
        # attempted fits).
        df = _random_walk_series(24, sigma_eta=0.05, sigma_eps=1e-6, seed=5)
        origin = self._origin_after(df)
        result = models.local_level_forecast(df, origin, HORIZON_NEXT)
        self.assertNotEqual(result, "FIT_FAILED")
        self.assertIsNotNone(result)
        quantiles, clamped = result
        self.assertTrue(clamped["sigma2.irregular"])
        self.assertFalse(clamped["sigma2.level"])
        values = [quantiles[q] for q in QUANTILE_LEVELS]
        self.assertEqual(values, sorted(values))

    def test_fit_exception_is_fit_failed(self):
        df = _random_walk_series(60, 0.05, 0.1, seed=2, freq="30D",
                                 start="2018-01-01")
        origin = self._origin_after(df)
        with unittest.mock.patch.object(
                models._LocalLevelTrend, "fit",
                side_effect=ValueError("boom")):
            self.assertEqual(
                models.local_level_forecast(df, origin, HORIZON_NEXT),
                "FIT_FAILED")

    def test_quantiles_are_monotone_and_centered_on_the_median(self):
        df = _random_walk_series(60, 0.05, 0.1, seed=2, freq="30D",
                                 start="2018-01-01")
        origin = self._origin_after(df)
        quantiles, _clamped = models.local_level_forecast(
            df, origin, HORIZON_NEXT)
        values = [quantiles[q] for q in QUANTILE_LEVELS]
        self.assertEqual(values, sorted(values))
        # Gaussian quantiles: symmetric around the median.
        self.assertAlmostEqual(
            (quantiles[0.025] + quantiles[0.975]) / 2, quantiles[0.5],
            places=6)
        self.assertAlmostEqual(
            (quantiles[0.1] + quantiles[0.9]) / 2, quantiles[0.5], places=6)

    def test_width_grows_with_horizon(self):
        # Same structural AC as 1.4's baselines (G4: "Intervallbreite
        # wächst mit Horizont") -- the Kalman state-uncertainty growth
        # over a longer forecast horizon is the mechanism, not an
        # artificial inflation.
        df = _random_walk_series(60, 0.05, 0.1, seed=2, freq="30D",
                                 start="2018-01-01")
        origin = self._origin_after(df)
        next_q, _ = models.local_level_forecast(df, origin, HORIZON_NEXT)
        m12_q, _ = models.local_level_forecast(df, origin, HORIZON_12M)
        width_next = next_q[0.9] - next_q[0.1]
        width_12m = m12_q[0.9] - m12_q[0.1]
        self.assertGreater(width_12m, width_next)

    def test_a_longer_gap_before_the_origin_widens_the_forecast(self):
        # 2.2's own mandated test: "Lücke von 24 M ⇒ Prognoseintervall
        # breiter als bei Lücke 1 M." Same underlying series, origin
        # moved further past the series' own last observation.
        df = _random_walk_series(60, 0.05, 0.1, seed=2, freq="30D",
                                 start="2018-01-01")
        last_month = pd.Timestamp(
            df["date"].iloc[-1].year, df["date"].iloc[-1].month, 1)
        near_origin = last_month + pd.DateOffset(months=1)
        far_origin = last_month + pd.DateOffset(months=24)
        near_q, _ = models.local_level_forecast(df, near_origin, HORIZON_NEXT)
        far_q, _ = models.local_level_forecast(df, far_origin, HORIZON_NEXT)
        self.assertGreater(
            far_q[0.9] - far_q[0.1], near_q[0.9] - near_q[0.1])

    def test_multi_lot_months_narrow_the_forecast_vs_a_single_lot_month(
            self):
        # 2.1/2.6 fix's whole point: a month with several lots should
        # pull the forecast's observation-noise contribution down
        # relative to an otherwise-identical series with one lot per
        # month, since sigma2.irregular/k_t shrinks with k_t.
        rng = np.random.default_rng(9)
        n = 36
        dates = pd.date_range("2018-01-01", periods=n, freq="MS")
        level = np.cumsum(rng.normal(0, 0.02, n))
        base_rows = []
        many_rows = []
        for i, d in enumerate(dates):
            y = level[i] + rng.normal(0, 0.2)
            base_rows.append((d.isoformat(), float(y), "koppe", 1))
            many_rows.append((d.isoformat(), float(y), "koppe", 1))
            if i % 3 == 0:
                for _ in range(5):
                    many_rows.append(
                        (d.isoformat(),
                         float(level[i] + rng.normal(0, 0.2)), "koppe", 1))
        df_base = _series(base_rows)
        df_many = _series(many_rows)
        origin = pd.Timestamp(dates[-1].year, dates[-1].month,
                              1) + pd.DateOffset(months=1)
        q_base, _ = models.local_level_forecast(df_base, origin,
                                                 HORIZON_NEXT)
        q_many, _ = models.local_level_forecast(df_many, origin,
                                                 HORIZON_NEXT)
        self.assertLess(q_many[0.9] - q_many[0.1],
                        q_base[0.9] - q_base[0.1])


class LocalLinearTrendForecastTest(unittest.TestCase):
    """2.6: local_linear_trend_forecast -- same contract as
    local_level_forecast, plus the mandatory damped slope."""

    def _origin_after(self, df):
        last = df["date"].iloc[-1]
        return pd.Timestamp(last.year, last.month, 1) + pd.DateOffset(
            months=1)

    def test_too_few_months_returns_none(self):
        df = _series([("2020-01-15", 1.0, "koppe", 1)])
        origin = self._origin_after(df)
        self.assertIsNone(
            models.local_linear_trend_forecast(df, origin, HORIZON_NEXT))

    def test_quantiles_are_monotone(self):
        rng = np.random.default_rng(13)
        n = 60
        dates = pd.date_range("2015-01-01", periods=n, freq="MS")
        level = np.linspace(0, 2, n) + rng.normal(0, 0.05, n)
        df = _series([(d.isoformat(), float(v), "koppe", 1)
                      for d, v in zip(dates, level)])
        origin = self._origin_after(df)
        result = models.local_linear_trend_forecast(df, origin, HORIZON_NEXT)
        self.assertIsNotNone(result)
        self.assertNotEqual(result, "FIT_FAILED")
        quantiles, _clamped = result
        values = [quantiles[q] for q in QUANTILE_LEVELS]
        self.assertEqual(values, sorted(values))

    def test_damping_keeps_the_12m_forecast_from_running_away(self):
        # 2.6's own mandatory requirement: an undamped trend extrapolated
        # 12 months out could produce fantasy prices. Compare the
        # trend-only forward move (median minus the last observed
        # level) against what an UNDAMPED linear extrapolation of the
        # same fitted slope would give over the same horizon -- the
        # damped forecast must move distinctly less.
        rng = np.random.default_rng(17)
        n = 48
        dates = pd.date_range("2016-01-01", periods=n, freq="MS")
        slope = 0.15
        level = slope * np.arange(n) + rng.normal(0, 0.03, n)
        df = _series([(d.isoformat(), float(v), "koppe", 1)
                      for d, v in zip(dates, level)])
        origin = self._origin_after(df)
        result = models.local_linear_trend_forecast(df, origin, HORIZON_12M)
        self.assertIsNotNone(result)
        self.assertNotEqual(result, "FIT_FAILED")
        quantiles, _clamped = result
        undamped_move = slope * 13  # 12m horizon + the 1 "next" step
        actual_move = quantiles[0.5] - level[-1]
        self.assertLess(actual_move, undamped_move)

    def test_fit_exception_is_fit_failed(self):
        df = _random_walk_series(60, 0.05, 0.1, seed=2, freq="30D",
                                 start="2018-01-01")
        origin = self._origin_after(df)
        with unittest.mock.patch.object(
                models._LocalLevelTrend, "fit",
                side_effect=ValueError("boom")):
            self.assertEqual(
                models.local_linear_trend_forecast(df, origin, HORIZON_NEXT),
                "FIT_FAILED")


class MakeLocalLevelForecasterTest(unittest.TestCase):
    def test_counters_track_calls_insufficient_and_fit_failed_separately(
            self):
        forecaster = models.make_local_level_forecaster()
        dates = pd.date_range("2018-01-01", periods=24, freq="MS")
        constant_df = _series([(d.isoformat(), 5.0, "koppe", 1)
                               for d in dates])
        too_short_df = _series([("2020-01-15", 1.0, "koppe", 1)])
        good_df = _random_walk_series(60, 0.05, 0.1, seed=2, freq="30D",
                                      start="2018-01-01")
        origin_const = pd.Timestamp("2020-02-01")
        origin_short = pd.Timestamp("2020-02-01")
        origin_good = pd.Timestamp(
            good_df["date"].iloc[-1].year,
            good_df["date"].iloc[-1].month, 1) + pd.DateOffset(months=1)

        r1 = forecaster(constant_df, origin_const, HORIZON_NEXT)
        r2 = forecaster(too_short_df, origin_short, HORIZON_NEXT)
        r3 = forecaster(good_df, origin_good, HORIZON_NEXT)

        self.assertIsNone(r1)
        self.assertIsNone(r2)
        self.assertIsInstance(r3, dict)
        self.assertEqual(forecaster.counters["n_calls"], 3)
        self.assertEqual(forecaster.counters["n_insufficient_months"], 1)
        self.assertEqual(forecaster.counters["n_fit_failed"], 1)

    def test_clamp_counters_increment_on_a_successful_clamped_fit(self):
        forecaster = models.make_local_level_forecaster()
        df = _random_walk_series(24, sigma_eta=0.05, sigma_eps=1e-6, seed=5)
        origin = pd.Timestamp(
            df["date"].iloc[-1].year, df["date"].iloc[-1].month,
            1) + pd.DateOffset(months=1)
        result = forecaster(df, origin, HORIZON_NEXT)
        self.assertIsInstance(result, dict)
        self.assertEqual(forecaster.counters["n_sigma2_irregular_clamped"], 1)
        self.assertEqual(forecaster.counters["n_sigma2_level_clamped"], 0)

    def test_never_returns_the_fit_failed_sentinel_itself(self):
        forecaster = models.make_local_level_forecaster()
        dates = pd.date_range("2018-01-01", periods=24, freq="MS")
        constant_df = _series([(d.isoformat(), 5.0, "koppe", 1)
                               for d in dates])
        result = forecaster(constant_df, pd.Timestamp("2020-02-01"),
                            HORIZON_NEXT)
        self.assertIsNone(result)
        self.assertNotEqual(result, "FIT_FAILED")


class MakeLocalLinearTrendForecasterTest(unittest.TestCase):
    def test_counters_track_calls_and_insufficient_months(self):
        forecaster = models.make_local_linear_trend_forecaster()
        too_short_df = _series([("2020-01-15", 1.0, "koppe", 1)])
        good_df = _random_walk_series(60, 0.05, 0.1, seed=2, freq="30D",
                                      start="2018-01-01")
        origin_short = pd.Timestamp("2020-02-01")
        origin_good = pd.Timestamp(
            good_df["date"].iloc[-1].year,
            good_df["date"].iloc[-1].month, 1) + pd.DateOffset(months=1)

        r1 = forecaster(too_short_df, origin_short, HORIZON_NEXT)
        r2 = forecaster(good_df, origin_good, HORIZON_NEXT)

        self.assertIsNone(r1)
        self.assertIsInstance(r2, dict)
        self.assertEqual(forecaster.counters["n_calls"], 2)
        self.assertEqual(forecaster.counters["n_insufficient_months"], 1)

    def test_counters_are_independent_per_forecaster_instance(self):
        # Same trap the local_level wrapper's own module comment in
        # run.py documents: counters must not leak across instances.
        f1 = models.make_local_linear_trend_forecaster()
        f2 = models.make_local_linear_trend_forecaster()
        too_short_df = _series([("2020-01-15", 1.0, "koppe", 1)])
        f1(too_short_df, pd.Timestamp("2020-02-01"), HORIZON_NEXT)
        self.assertEqual(f1.counters["n_calls"], 1)
        self.assertEqual(f2.counters["n_calls"], 0)


if __name__ == "__main__":
    unittest.main()
