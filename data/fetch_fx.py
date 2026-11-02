"""Fetch historical EUR FX rates from EODHD into a local JSON cache.

One file per currency (``EUR<CCY>.json``) holding units of <CCY> per 1 EUR,
taken from the daily close of the ``EUR<CCY>.FOREX`` series. ``build_db.py``
loads the cache offline (``_load_fx_rates``), so the DB build never needs the
network or the API token.

    EODHD_API_TOKEN=... python3 data/fetch_fx.py [--currencies AUD,USD] [--from 1998-01-01]

Env:
  EODHD_API_TOKEN  API token (required; never logged, never written to disk)
  FX_CACHE_PATH    cache dir (default: /Volumes/samsung/winefeed-data/fx)
"""
import argparse
import datetime
import http.client
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# Currencies present in the master DB with a market rate. NLG is excluded: it
# has a legal fix rate (build_db._FX_FIX).
CURRENCIES = ["AUD", "USD", "GBP", "CHF", "HKD", "SGD", "CNY"]
DEFAULT_FROM = "1998-01-01"
MAX_RATE = 1e6  # sanity bound; HKD/CNY/AUD are < 100 per EUR
BASE_URL = "https://eodhd.com/api/eod/"
FX_CACHE = os.environ.get("FX_CACHE_PATH", "/Volumes/samsung/winefeed-data/fx")


class FxFetchError(RuntimeError):
    pass


def build_url(currency, token, date_from, date_to):
    query = urllib.parse.urlencode({
        "api_token": token, "fmt": "json", "period": "d",
        "from": date_from, "to": date_to})
    return f"{BASE_URL}EUR{currency}.FOREX?{query}"


def parse_eod(payload, currency):
    """EODHD EOD list -> sorted ``[[date, close], ...]``; raises on bad shape."""
    if not isinstance(payload, list) or not payload:
        raise FxFetchError(f"EUR{currency}: empty or non-list response")
    rows = {}
    for rec in payload:
        try:
            date = datetime.date.fromisoformat(rec["date"]).isoformat()
            close = rec["close"]
        except (KeyError, TypeError, ValueError) as e:
            raise FxFetchError(f"EUR{currency}: malformed record {rec!r}") from e
        if (isinstance(close, bool) or not isinstance(close, (int, float))
                or not math.isfinite(close) or not 0 < close < MAX_RATE):
            raise FxFetchError(
                f"EUR{currency}: implausible close {close!r} on {date}")
        close = float(close)
        rows[date] = close
    return [[d, rows[d]] for d in sorted(rows)]


def _mask(text, token):
    """Hide the token in every form it can take inside a URL."""
    for form in (token, urllib.parse.quote(token), urllib.parse.quote_plus(token),
                 urllib.parse.quote(token, safe="")):
        text = text.replace(form, "***")
    return text


def fetch_pair(currency, token, date_from, date_to, opener=urllib.request.urlopen):
    url = build_url(currency, token, date_from, date_to)
    try:
        with opener(url, timeout=60) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, OSError, ValueError,
            http.client.HTTPException) as e:
        # Never echo the URL: it carries the API token.
        raise FxFetchError(
            f"EUR{currency}: request failed ({type(e).__name__}: "
            f"{_mask(str(e), token)})") from None
    return parse_eod(payload, currency)


def _existing(path):
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        return doc["first_date"], len(doc["rows"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write_cache(cache_dir, currency, rows, date_from, date_to, now=None,
                force=False):
    """Atomically write the cache; refuse a result that shrinks the history."""
    os.makedirs(cache_dir, exist_ok=True)
    path = os.path.join(cache_dir, f"EUR{currency}.json")
    old = _existing(path)
    if old and not force and (rows[0][0] > old[0] or len(rows) < 0.9 * old[1]):
        raise FxFetchError(
            f"EUR{currency}: new data ({rows[0][0]}, {len(rows)} days) shrinks "
            f"existing cache ({old[0]}, {old[1]} days); use --force to overwrite")
    doc = {
        "source": "EODHD", "ticker": f"EUR{currency}.FOREX",
        "currency": currency, "unit": "units of currency per 1 EUR",
        "requested_from": date_from, "requested_to": date_to,
        "first_date": rows[0][0], "last_date": rows[-1][0],
        "fetched_at": (now or datetime.datetime.now(datetime.timezone.utc)
                       ).isoformat(timespec="seconds"),
        "rows": rows,
    }
    tmp = f"{path}.tmp.{os.getpid()}"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, allow_nan=False)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


def main(argv=None, opener=urllib.request.urlopen):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--currencies", default=",".join(CURRENCIES))
    ap.add_argument("--from", dest="date_from", default=DEFAULT_FROM)
    # Default to yesterday (UTC): today's close is provisional until the day ends.
    ap.add_argument("--to", dest="date_to", default=(
        datetime.datetime.now(datetime.timezone.utc).date()
        - datetime.timedelta(days=1)).isoformat())
    ap.add_argument("--force", action="store_true",
                    help="overwrite a cache even if the new history is shorter")
    ap.add_argument("--cache", default=FX_CACHE)
    args = ap.parse_args(argv)

    token = os.environ.get("EODHD_API_TOKEN")
    if not token:
        print("EODHD_API_TOKEN not set", file=sys.stderr)
        return 2
    failed = 0
    for ccy in [c.strip().upper() for c in args.currencies.split(",") if c.strip()]:
        try:
            rows = fetch_pair(ccy, token, args.date_from, args.date_to, opener)
        except FxFetchError as e:
            print(f"FAIL {e}", file=sys.stderr)
            failed += 1
            continue
        try:
            write_cache(args.cache, ccy, rows, args.date_from, args.date_to,
                        force=args.force)
        except FxFetchError as e:
            print(f"FAIL {e}", file=sys.stderr)
            failed += 1
            continue
        late = " (WARN: starts after --from)" if rows[0][0] > args.date_from else ""
        print(f"  EUR{ccy}: {len(rows)} days {rows[0][0]} .. {rows[-1][0]}{late}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
