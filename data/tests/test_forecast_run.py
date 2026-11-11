"""forecast.run._build_forecasters -- senior-review finding: an earlier
version built the local_level forecaster (and its mutable .counters
closure) once at module-import time, so repeated main() calls in one
process would silently accumulate counts across runs."""
# pylint: disable=protected-access
import unittest

from forecast import run


class BuildForecastersTest(unittest.TestCase):
    def test_each_call_returns_fresh_local_level_counters(self):
        first = run._build_forecasters()
        first["local_level"].counters["n_calls"] = 42
        second = run._build_forecasters()
        self.assertEqual(second["local_level"].counters["n_calls"], 0)
        self.assertIsNot(
            first["local_level"].counters, second["local_level"].counters)

    def test_model_names_match_build_forecasters_keys(self):
        forecasters = run._build_forecasters()
        self.assertEqual(set(forecasters), set(run._MODEL_NAMES))


if __name__ == "__main__":
    unittest.main()
