"""1.5 AC ("reproduzierbar per Befehl"): CLI that (re-)generates
``docs/forecast-baseline-report.md`` against the live master DB.

    python3 -m forecast.run --db /Volumes/samsung/winefeed-data/wine_auction_prices.sqlite

G6: opens the DB read-only (``mode=ro``) -- this package never writes
back into the master DB, only (eventually, Stufe 5) into its own
``price_forecasts`` table via the normal atomic build.
"""
import argparse
import datetime
import sqlite3

from . import eval as feval
from . import models as fmodels

# 1.4's four naive baselines -- see models.BASELINES. Stufe 2 adds
# local_level (2.1-2.4) and local_linear_trend (2.6) alongside them,
# never replacing them (G2: every later model must keep beating these
# on the same report). Neither is in the default set below -- a Kalman
# MLE fit is far slower than a baseline's microseconds-per-call, so
# including either by default would silently turn an ordinary
# baseline-only report run into a much longer one. Select them
# explicitly with --models.
#
# Only NAMES live at module level, not forecaster instances -- senior-
# review finding: an earlier version built
# ``fmodels.make_local_level_forecaster()`` once here, at import time,
# so its ``.counters`` dict was one shared, mutable closure reused by
# every ``main()`` call. Harmless for the normal one-shot CLI
# invocation, but a real trap for anything that imports this module
# and calls ``main()`` more than once in the same process (a test, a
# notebook, a future scheduler) -- counts would silently accumulate
# across runs instead of resetting. Each ``main()`` call now builds its
# own fresh forecaster instances instead.
_MODEL_NAMES = (list(fmodels.BASELINES)
               + ["local_level", "local_linear_trend"])


def _build_forecasters():
    forecasters = dict(fmodels.BASELINES)
    forecasters["local_level"] = fmodels.make_local_level_forecaster()
    forecasters["local_linear_trend"] = (
        fmodels.make_local_linear_trend_forecaster())
    return forecasters


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="path to the master DB")
    parser.add_argument(
        "--as-of", default=None,
        help="ISO date to evaluate as-of (default: today, G5 note: pass"
        " this explicitly for a reproducible run)")
    parser.add_argument(
        "--out", default="docs/forecast-baseline-report.md")
    parser.add_argument(
        "--models", default=",".join(fmodels.BASELINES),
        help="comma-separated subset of " +
        ",".join(_MODEL_NAMES) +
        " (default: the 1.4 baselines only -- local_level opts in"
        " explicitly, see this module's own comment)")
    args = parser.parse_args()

    names = [n.strip() for n in args.models.split(",") if n.strip()]
    unknown = [n for n in names if n not in _MODEL_NAMES]
    if unknown:
        parser.error(f"unknown model(s): {unknown}; choose from "
                     f"{sorted(_MODEL_NAMES)}")
    all_forecasters = _build_forecasters()
    forecasters = {n: all_forecasters[n] for n in names}

    as_of = args.as_of or datetime.date.today().isoformat()
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        feval.write_baseline_report(conn, forecasters, as_of, args.out)
    finally:
        conn.close()
    for name, forecaster in forecasters.items():
        counters = getattr(forecaster, "counters", None)
        if counters:
            print(f"{name}: {counters}")
    print(f"wrote {args.out} (as_of={as_of}, {len(forecasters)} model(s): "
         f"{', '.join(forecasters)})")


if __name__ == "__main__":
    main()
