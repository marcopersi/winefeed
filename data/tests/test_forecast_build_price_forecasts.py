"""forecast.build_price_forecasts -- Stufe 5.1/5.2. Pure-logic tests
with a fake ``Forecaster`` (no Kalman fit, no DB) for ``forecast_row``'s
calibration/flag wiring, plus one small in-memory-DB test for the
schema + idempotent delete-then-insert of ``build``."""
# pylint: disable=protected-access
# -- protected-access: exercising the module's internal _correction/
# _decision helpers directly.
import math
import sqlite3
import unittest
from unittest import mock

import pandas as pd

from forecast import build_price_forecasts as bpf
from forecast.models import HORIZON_NEXT, HORIZON_12M

_AS_OF = pd.Timestamp("2026-11-20")
_CREATED_AT = "2026-11-20T00:00:00+00:00"


def _series_df(prices):
    dates = pd.date_range("2024-01-01", periods=len(prices), freq="MS")
    return pd.DataFrame({"date": dates, "y": prices})


def _fake_forecaster(result):
    def forecaster(_train, _origin, _horizon):
        return result
    forecaster.counters = {"n_calls": 0}  # real Forecasters always carry this
    return forecaster


# All quantile values here are LOG-y (the model's own space, see D8 in
# forecast/data.py) -- forecast_row is responsible for exp()-ing them
# into real EUR before they land in a row/DB column.
_QUANTILES = {0.025: 0.0, 0.10: 0.3, 0.25: 0.6, 0.50: 1.0, 0.75: 1.4,
             0.90: 1.7, 0.975: 2.0}

_CALIB_FORECAST = {
    "correction": {
        "3-4": {"0.5": 0.2, "0.8": 0.4, "0.95": 0.6},
        "_pooled": {"0.5": 0.9, "0.8": 0.9, "0.95": 0.9},
    },
    "decision": {"3-4": "forecast"},
}
_CALIB_INSUFFICIENT = {
    "correction": {"3-4": {"0.5": 0.2, "0.8": 0.4, "0.95": 0.6}},
    "decision": {"3-4": "INSUFFICIENT_DATA"},
}


class ForecastRowTests(unittest.TestCase):
    def test_no_observations_returns_none(self):
        row = bpf.forecast_row(
            (1, 2020, 75.0), _series_df([]), HORIZON_NEXT, _CALIB_FORECAST,
            _AS_OF, _CREATED_AT, _fake_forecaster(None))
        self.assertIsNone(row)

    def test_forecaster_returns_none_is_insufficient_data(self):
        df = _series_df([1.0, 1.0, 1.0, 1.0])  # density_class "3-4"
        row = bpf.forecast_row(
            (1, 2020, 75.0), df, HORIZON_NEXT, _CALIB_FORECAST, _AS_OF,
            _CREATED_AT, _fake_forecaster(None))
        self.assertEqual(row["flags"], "INSUFFICIENT_DATA")
        self.assertIsNone(row["median_eur"])
        self.assertEqual(row["n_obs"], 4)

    def test_decision_insufficient_data_suppresses_point_value(self):
        df = _series_df([1.0, 1.0, 1.0, 1.0])
        row = bpf.forecast_row(
            (1, 2020, 75.0), df, HORIZON_NEXT, _CALIB_INSUFFICIENT, _AS_OF,
            _CREATED_AT, _fake_forecaster(dict(_QUANTILES)))
        self.assertEqual(row["flags"], "INSUFFICIENT_DATA")
        self.assertIsNone(row["median_eur"])
        self.assertIsNone(row["q10_eur"])

    def test_decision_forecast_fills_calibrated_bands_in_eur(self):
        # 4 flat observations at y=1.0 -> last_y=1.0, median=1.0 (log) ->
        # log_ratio=0, well inside the extrapolation bound -> no flag.
        df = _series_df([1.0, 1.0, 1.0, 1.0])
        row = bpf.forecast_row(
            (1, 2020, 75.0), df, HORIZON_NEXT, _CALIB_FORECAST, _AS_OF,
            _CREATED_AT, _fake_forecaster(dict(_QUANTILES)))
        self.assertIsNone(row["flags"])
        self.assertAlmostEqual(row["median_eur"], math.exp(1.0))
        # level 0.8 -> correction 0.4 (density_class "3-4"), in log-space,
        # exp()-ed only after the +/- -- never exp(0.4)*median.
        self.assertAlmostEqual(row["q10_eur"], math.exp(1.0 - 0.4))
        self.assertAlmostEqual(row["q90_eur"], math.exp(1.0 + 0.4))
        # level 0.95 -> correction 0.6
        self.assertAlmostEqual(row["q025_eur"], math.exp(1.0 - 0.6))
        self.assertAlmostEqual(row["q975_eur"], math.exp(1.0 + 0.6))

    def test_extrapolation_flag_set_but_still_forecasts(self):
        # last observation y=1.0, median forecast y=5.0 -> log_ratio=4.0,
        # far outside [ln(0.2), ln(5)] -> EXTRAPOLATION, but the decision
        # is still "forecast" (plan 5.5: visible flag, not suppression).
        df = _series_df([1.0, 1.0, 1.0, 1.0])
        extreme = dict(_QUANTILES)
        extreme[0.50] = 5.0
        row = bpf.forecast_row(
            (1, 2020, 75.0), df, HORIZON_NEXT, _CALIB_FORECAST, _AS_OF,
            _CREATED_AT, _fake_forecaster(extreme))
        self.assertEqual(row["flags"], "EXTRAPOLATION")
        self.assertAlmostEqual(row["median_eur"], math.exp(5.0))

    def test_pooled_fallback_used_for_unknown_density_class(self):
        # density_class "1-2" is absent from this calibration fixture's
        # "correction" dict -> falls back to "_pooled".
        df = _series_df([1.0, 1.0])
        calib = {
            "correction": {"_pooled": {"0.5": 0.9, "0.8": 0.9, "0.95": 0.9}},
            "decision": {"1-2": "forecast"},
        }
        row = bpf.forecast_row(
            (1, 2020, 75.0), df, HORIZON_NEXT, calib, _AS_OF, _CREATED_AT,
            _fake_forecaster(dict(_QUANTILES)))
        self.assertAlmostEqual(row["q10_eur"], math.exp(1.0 - 0.9))

    def test_decision_missing_entirely_is_insufficient_data(self):
        # density_class not present in "decision" at all (e.g. never
        # seen in that horizon's TEST split) -> conservative default.
        df = _series_df([1.0, 1.0, 1.0, 1.0])
        calib = {"correction": {"_pooled": {"0.5": 0.9, "0.8": 0.9,
                                           "0.95": 0.9}},
                "decision": {}}
        row = bpf.forecast_row(
            (1, 2020, 75.0), df, HORIZON_NEXT, calib, _AS_OF, _CREATED_AT,
            _fake_forecaster(dict(_QUANTILES)))
        self.assertEqual(row["flags"], "INSUFFICIENT_DATA")
        self.assertIsNone(row["median_eur"])


class BuildTests(unittest.TestCase):
    def test_build_creates_schema_and_is_idempotent_per_model_version(self):
        conn = sqlite3.connect(":memory:")
        calibration = {HORIZON_NEXT: _CALIB_FORECAST,
                      HORIZON_12M: _CALIB_FORECAST}
        series = [((1, 2020, 75.0), _series_df([1.0, 1.0, 1.0, 1.0]))]
        with mock.patch.object(bpf.data, "load_all_series",
                              return_value=series):
            with mock.patch.object(
                    bpf.fmodels, "make_local_level_forecaster",
                    return_value=_fake_forecaster(dict(_QUANTILES))):
                n_first = bpf.build(conn, calibration, "2026-11-20")
                n_second = bpf.build(conn, calibration, "2026-11-20")
        self.assertEqual(n_first, 2)  # 1 series x 2 horizons
        self.assertEqual(n_second, 2)
        total = conn.execute(
            "SELECT COUNT(*) FROM price_forecasts").fetchone()[0]
        # Rerunning with the same MODEL_VERSION must replace, not append.
        self.assertEqual(total, 2)
        row = conn.execute(
            "SELECT wine_ref_id, vintage, size_class, horizon, median_eur"
            " FROM price_forecasts WHERE horizon = ?",
            (HORIZON_NEXT,)).fetchone()
        self.assertEqual(row[:4], (1, 2020, 75.0, HORIZON_NEXT))
        self.assertAlmostEqual(row[4], math.exp(1.0))


if __name__ == "__main__":
    unittest.main()
