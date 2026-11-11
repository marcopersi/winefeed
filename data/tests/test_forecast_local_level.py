"""2.2-2.4: forecast.models.local_level_forecast -- UnobservedComponents
('local level') on a monthly-aggregated grid, its prediction-interval
quantiles, and the FIT_FAILED variance-floor/convergence guards.
"""
# pylint: disable=protected-access
import unittest
import unittest.mock

import numpy as np
import pandas as pd
import statsmodels.api as sm

from forecast import models
from forecast.models import HORIZON_NEXT, HORIZON_12M, QUANTILE_LEVELS


def _series(rows):
    df = pd.DataFrame(rows, columns=["date", "y", "provider", "qty"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def _random_walk_series(n, sigma_eta, sigma_eps, seed, freq="MS",
                        start="2000-01-01"):
    rng = np.random.default_rng(seed)
    dates = pd.date_range(start, periods=n, freq=freq)
    level = np.cumsum(rng.normal(0, sigma_eta, n))
    y = level + rng.normal(0, sigma_eps, n)
    return _series([(d.isoformat(), float(v), "koppe", 1)
                    for d, v in zip(dates, y)])


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


class MonthsBetweenTest(unittest.TestCase):
    def test_counts_calendar_months_not_days(self):
        self.assertEqual(
            models._months_between("2023-01-01", "2023-07-01"), 6)
        self.assertEqual(
            models._months_between("2023-12-01", "2024-01-01"), 1)
        self.assertEqual(
            models._months_between("2023-01-15", "2023-02-01"), 1)


class LocalLevelRecoversKnownVarianceTest(unittest.TestCase):
    def test_sigma2_estimates_within_30_percent(self):
        # Fixed seed (G5), >= 200 months -- a short series won't recover
        # within 30% (MLE sampling noise dominates). Verified empirically
        # before writing this assertion, not assumed: seed=0 converges
        # with both ratios comfortably inside [0.7, 1.3].
        sigma_eta, sigma_eps = 0.08, 0.15
        df = _random_walk_series(240, sigma_eta, sigma_eps, seed=0)
        monthly = models._monthly_series(df)
        res = sm.tsa.UnobservedComponents(
            monthly, level="local level").fit(disp=False)
        self.assertTrue(res.mle_retvals.get("converged"))
        est_eta = res.params["sigma2.level"] ** 0.5
        est_eps = res.params["sigma2.irregular"] ** 0.5
        self.assertAlmostEqual(est_eta / sigma_eta, 1.0, delta=0.3)
        self.assertAlmostEqual(est_eps / sigma_eps, 1.0, delta=0.3)


class PredictionIntervalIncludesMeasurementNoiseTest(unittest.TestCase):
    def test_forecast_variance_is_at_least_the_observation_noise_variance(
            self):
        # 2.4's own mandated test: "Prädiktions- nicht Konfidenz-
        # intervall (Messrauschen einrechnen!)". Confirmed empirically
        # (not assumed from statsmodels docs) that
        # get_forecast(h).var_pred_mean already equals filtered state
        # variance PLUS sigma2.irregular -- this pins that fact down as
        # a regression test, since local_level_forecast relies on it
        # without adding sigma2.irregular manually anywhere.
        df = _random_walk_series(200, sigma_eta=0.0, sigma_eps=0.2, seed=1)
        monthly = models._monthly_series(df)
        res = sm.tsa.UnobservedComponents(
            monthly, level="local level").fit(disp=False)
        sigma2_irregular = res.params["sigma2.irregular"]
        for h in (1, 6, 24):
            var = res.get_forecast(h).var_pred_mean.iloc[-1]
            self.assertGreaterEqual(var, sigma2_irregular)


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
                sm.tsa.UnobservedComponents, "fit",
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


if __name__ == "__main__":
    unittest.main()
