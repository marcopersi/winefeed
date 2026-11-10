"""1.4: forecast.models' four naive baselines + the shared "quantiles
via empirical residuals" machinery they're built on."""
# pylint: disable=protected-access
import unittest

import numpy as np
import pandas as pd

from forecast import models
from forecast.models import HORIZON_NEXT, HORIZON_12M, QUANTILE_LEVELS


def _series(rows):
    df = pd.DataFrame(rows, columns=["date", "y", "provider", "qty"])
    df["date"] = pd.to_datetime(df["date"])
    return df


class PointFnTest(unittest.TestCase):
    """Each point_fn against a small hand-built series."""

    def setUp(self):
        self.sub = _series([
            ("2020-01-01", 1.0, "koppe", 1),
            ("2020-07-01", 2.0, "koppe", 1),
            ("2021-01-01", 3.0, "koppe", 1),
        ])

    def test_last_value(self):
        self.assertEqual(
            models._last_value(self.sub, pd.Timestamp("2021-07-01")), 3.0)

    def test_last_value_empty_is_none(self):
        self.assertIsNone(
            models._last_value(self.sub.iloc[0:0], pd.Timestamp("2021-01-01")))

    def test_median_last_k_with_k_bigger_than_n_is_plain_median(self):
        # k=5 default, only 3 rows -- same as a plain median over all.
        got = models._median_last_k(self.sub, pd.Timestamp("2021-07-01"))
        self.assertAlmostEqual(got, 2.0)

    def test_rolling_median_12m_ignores_target_date(self):
        # The window is anchored on sub's OWN last date, not
        # target_date -- two wildly different target_dates give the
        # identical result (see _rolling_median_12m's docstring for why
        # anchoring on target_date instead is structurally broken for
        # the 12m horizon).
        a = models._rolling_median_12m(self.sub, pd.Timestamp("2021-02-01"))
        b = models._rolling_median_12m(self.sub, pd.Timestamp("2030-01-01"))
        self.assertEqual(a, b)

    def test_rolling_median_12m_excludes_rows_older_than_the_window(self):
        sub = _series([
            ("2019-06-01", 10.0, "koppe", 1),  # > 12m before 2021-01-01
            ("2020-01-01", 1.0, "koppe", 1),
            ("2020-07-01", 2.0, "koppe", 1),
            ("2021-01-01", 3.0, "koppe", 1),
        ])
        got = models._rolling_median_12m(sub, pd.Timestamp("2021-07-01"))
        self.assertAlmostEqual(got, 2.0)  # median of [1, 2, 3], not 10

    def test_rolling_median_12m_short_span_uses_every_row(self):
        # sub's own span is well under 12 months -- the window can
        # never be empty (it always includes at least sub's own last
        # row), so this falls back to a median over everything, same
        # as (b) with k >= n.
        got = models._rolling_median_12m(self.sub, pd.Timestamp("2021-07-01"))
        self.assertAlmostEqual(got, 2.0)

    def test_trend_recovers_exact_linear_series(self):
        # y = 2 + 0.5*t (t in years since first obs) -- an exact noiseless
        # line; OLS must recover both the slope and an extrapolated point
        # to (near-)machine precision.
        dates = pd.date_range("2015-01-01", periods=10, freq="365D")
        t_years = (dates - dates[0]).days / 365.25
        y = 2.0 + 0.5 * t_years
        sub = _series([(d.isoformat(), float(v), "koppe", 1)
                       for d, v in zip(dates, y)])
        target = dates[0] + pd.DateOffset(years=12)
        got = models._trend(sub, target)
        # Same day-count/365.25 convention _trend itself uses -- a
        # calendar "+12 years" offset isn't exactly 12*365.25 days
        # (leap-year count depends on which years it spans), so the
        # expected value must be derived the same way, not assumed.
        x_target = (target - dates[0]).days / 365.25
        expected = 2.0 + 0.5 * x_target
        self.assertAlmostEqual(got, expected, places=6)

    def test_trend_needs_two_distinct_dates(self):
        same_day = _series([
            ("2020-01-01", 1.0, "koppe", 1),
            ("2020-01-01", 2.0, "koppe", 1),
        ])
        self.assertIsNone(
            models._trend(same_day, pd.Timestamp("2020-06-01")))

    def test_trend_needs_at_least_two_rows(self):
        one_row = _series([("2020-01-01", 1.0, "koppe", 1)])
        self.assertIsNone(models._trend(one_row, pd.Timestamp("2020-06-01")))


class ConstantSeriesTest(unittest.TestCase):
    """1.4 AC: "Konstante Serie => Prognose konstant, Intervallbreite 0"."""

    def _constant_series(self, n=40, value=1.2345):
        # Span must exceed 12 months, or the 12m-horizon backtest finds
        # no residual pair at all and returns None (a real, separate
        # outcome -- see NonePropagationTest -- not what this test is
        # checking).
        dates = pd.date_range("2020-01-01", periods=n, freq="30D")
        return _series([(d.isoformat(), value, "koppe", 1) for d in dates])

    def test_every_baseline_is_constant_with_zero_width(self):
        series = self._constant_series()
        origin = series["date"].iloc[-1] + pd.Timedelta(days=1)
        for name, forecaster in models.BASELINES.items():
            for horizon in (HORIZON_NEXT, HORIZON_12M):
                forecast = forecaster(series, origin, horizon)
                self.assertIsNotNone(forecast, name)
                values = set(round(v, 9) for v in forecast.values())
                self.assertEqual(
                    len(values), 1,
                    f"{name}/{horizon}: expected one constant value,"
                    f" got {forecast}")
                self.assertAlmostEqual(
                    forecast[0.5], 1.2345, places=6, msg=name)


class WidthGrowsWithHorizonTest(unittest.TestCase):
    """G4: "Intervallbreite wächst mit Horizont" -- the structural test,
    not just the trivial constant-series case."""

    def test_last_value_12m_interval_wider_than_next(self):
        # A noisy random walk (fixed seed, G5): last_value's "next"
        # residual is one step's noise; its "12m" residual is the SUM
        # of ~12-13 steps' noise, so its variance -- and therefore the
        # derived quantile spread -- is naturally larger. A perfectly
        # deterministic drift (no noise) would give an exact, constant
        # residual at every horizon and a zero-width interval at BOTH
        # -- there would be nothing here to grow.
        rng = np.random.default_rng(42)
        dates = pd.date_range("2015-01-01", periods=96, freq="30D")
        steps = 0.01 + rng.normal(0, 0.05, size=len(dates))
        y = np.cumsum(steps)
        series = _series([(d.isoformat(), float(v), "koppe", 1)
                          for d, v in zip(dates, y)])
        origin = series["date"].iloc[-1] + pd.Timedelta(days=1)
        forecaster = models.BASELINES["last_value"]
        next_fc = forecaster(series, origin, HORIZON_NEXT)
        m12_fc = forecaster(series, origin, HORIZON_12M)
        self.assertIsNotNone(next_fc)
        self.assertIsNotNone(m12_fc)
        width_next = next_fc[0.90] - next_fc[0.10]
        width_12m = m12_fc[0.90] - m12_fc[0.10]
        self.assertGreater(width_12m, width_next)


class NonePropagationTest(unittest.TestCase):
    def test_too_few_rows_returns_none_for_both_horizons(self):
        series = _series([("2020-01-01", 1.0, "koppe", 1)])  # n < MIN_OBS
        origin = pd.Timestamp("2020-02-01")
        for name, forecaster in models.BASELINES.items():
            self.assertIsNone(
                forecaster(series, origin, HORIZON_NEXT), name)
            self.assertIsNone(
                forecaster(series, origin, HORIZON_12M), name)

    def test_12m_can_be_insufficient_while_next_still_forecasts(self):
        # Three rows a week apart -- "next" has 2 residuals (row 2 vs.
        # row 1, row 3 vs. rows 1-2), enough to clear the >= 2 floor;
        # "12m" has none (no row is ever >= 12 months after another in
        # this short series), so only "12m" must come back None.
        series = _series([
            ("2023-01-01", 1.0, "koppe", 1),
            ("2023-01-08", 1.0, "koppe", 1),
            ("2023-01-15", 1.0, "koppe", 1),
        ])
        origin = series["date"].iloc[-1] + pd.Timedelta(days=1)
        forecaster = models.BASELINES["last_value"]
        self.assertIsNotNone(forecaster(series, origin, HORIZON_NEXT))
        self.assertIsNone(forecaster(series, origin, HORIZON_12M))

    def test_exactly_one_residual_is_still_insufficient(self):
        # Confirmed real bug (senior-review self-check): a 2-row series
        # clears MIN_OBS (len(train) >= 2) but produces exactly ONE
        # "next" residual (row 2 vs. row 1) -- a single data point has
        # no spread to measure, so this must come back None, not a
        # confident-looking zero-width interval. This is exactly the
        # live report's old "n_train=1-2" artifact (Breite 50/80/95% =
        # 0.000 for every baseline) before the >= 2 floor existed.
        series = _series([
            ("2023-01-01", 1.0, "koppe", 1),
            ("2023-01-08", 1.0, "koppe", 1),
        ])
        origin = series["date"].iloc[-1] + pd.Timedelta(days=1)
        for name, forecaster in models.BASELINES.items():
            self.assertIsNone(
                forecaster(series, origin, HORIZON_NEXT), name)


class RetrospectiveResidualsCapTest(unittest.TestCase):
    """Performance fix: a real series with ~2000 training rows made the
    uncapped backtest O(n^2) (killed the live report run after 20+
    minutes). The cap must bound the residual COUNT and must not
    change behaviour at all for a series shorter than the cap."""

    def test_residual_count_never_exceeds_the_cap(self):
        dates = pd.date_range("2000-01-01", periods=500, freq="7D")
        series = _series([(d.isoformat(), float(i), "koppe", 1)
                          for i, d in enumerate(dates)])
        residuals = models._retrospective_residuals(
            series, models._last_value, HORIZON_NEXT)
        self.assertEqual(len(residuals), models.MAX_BACKTEST_STEPS)

    def test_short_series_is_unaffected_by_the_cap(self):
        dates = pd.date_range("2020-01-01", periods=10, freq="30D")
        series = _series([(d.isoformat(), float(i), "koppe", 1)
                          for i, d in enumerate(dates)])
        residuals = models._retrospective_residuals(
            series, models._last_value, HORIZON_NEXT)
        self.assertEqual(len(residuals), len(series) - 1)

    def test_a_large_series_still_completes_quickly(self):
        import time
        dates = pd.date_range("2000-01-01", periods=2000, freq="3D")
        series = _series([(d.isoformat(), 0.01 * i, "koppe", 1)
                          for i, d in enumerate(dates)])
        origin = series["date"].iloc[-1] + pd.Timedelta(days=1)
        t0 = time.time()
        for horizon in (HORIZON_NEXT, HORIZON_12M):
            self.assertIsNotNone(
                models.BASELINES["trend"](series, origin, horizon))
        elapsed = time.time() - t0
        self.assertLess(elapsed, 5.0)


class QuantilesFromResidualsTest(unittest.TestCase):
    def test_monotone_and_bias_corrected(self):
        residuals = [-1.0, -0.5, 0.0, 0.5, 1.0]
        q = models._quantiles_from_residuals(10.0, residuals)
        values = [q[lvl] for lvl in QUANTILE_LEVELS]
        self.assertEqual(values, sorted(values))
        self.assertAlmostEqual(q[0.5], 10.0, places=9)

    def test_biased_residuals_shift_the_median_away_from_point(self):
        # All-positive residuals (point_fn is systematically too low) --
        # q0.5 must be bias-corrected upward, not left at the raw point.
        residuals = [1.0, 2.0, 3.0]
        q = models._quantiles_from_residuals(10.0, residuals)
        self.assertGreater(q[0.5], 10.0)


if __name__ == "__main__":
    unittest.main()
