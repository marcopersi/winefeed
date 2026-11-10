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
from .models import BASELINES

# 1.4's four naive baselines -- see models.BASELINES. Stufe 2+ adds
# real models here alongside them, never replacing them (G2: every
# later model must keep beating these on the same report).
FORECASTERS = dict(BASELINES)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="path to the master DB")
    parser.add_argument(
        "--as-of", default=None,
        help="ISO date to evaluate as-of (default: today, G5 note: pass"
        " this explicitly for a reproducible run)")
    parser.add_argument(
        "--out", default="docs/forecast-baseline-report.md")
    args = parser.parse_args()

    as_of = args.as_of or datetime.date.today().isoformat()
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    try:
        feval.write_baseline_report(conn, FORECASTERS, as_of, args.out)
    finally:
        conn.close()
    print(f"wrote {args.out} (as_of={as_of}, {len(FORECASTERS)} model(s))")


if __name__ == "__main__":
    main()
