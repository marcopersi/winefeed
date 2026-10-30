"""FX rates: EODHD fetch (mocked, no network) and offline cache -> fx_rates."""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402
import fetch_fx  # noqa: E402

TOKEN = "SECRET-TOKEN-123"


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _opener(payload, seen=None):
    def op(url, timeout=None):
        if seen is not None:
            seen.append(url)
        return _Resp(json.dumps(payload).encode())
    return op


def _eod(*pairs):
    return [{"date": d, "close": c, "open": c} for d, c in pairs]


class FetchTest(unittest.TestCase):
    def test_url_and_parse_sorted_deduped(self):
        seen = []
        rows = fetch_fx.fetch_pair(
            "USD", TOKEN, "2020-01-01", "2020-01-31",
            _opener(_eod(("2020-01-03", 1.1), ("2020-01-02", 1.2),
                         ("2020-01-03", 1.15)), seen))
        self.assertEqual(rows, [["2020-01-02", 1.2], ["2020-01-03", 1.15]])
        self.assertIn("EURUSD.FOREX", seen[0])
        self.assertIn("from=2020-01-01", seen[0])

    def test_bad_payloads_rejected(self):
        inf = [{"date": "2020-01-02", "close": float("inf")}]
        for payload in (inf, [{"date": "2020-01-02", "close": True}],
                        [{"date": "2020-01-02", "close": "1.1"}],
                        _eod(("2020-01-02", 1e9)),
                        [], {"x": 1}, _eod(("2020-01-02", 0)),
                        _eod(("2020-01-02", -1.0)),
                        _eod(("not-a-date", 1.0)), [{"date": "2020-01-02"}]):
            with self.assertRaises(fetch_fx.FxFetchError, msg=str(payload)):
                fetch_fx.fetch_pair("USD", TOKEN, "a", "b", _opener(payload))

    def test_token_never_in_error(self):
        def boom(url, timeout=None):
            raise urllib.error.URLError(f"failed for {url}")
        with self.assertRaises(fetch_fx.FxFetchError) as cm:
            fetch_fx.fetch_pair("USD", TOKEN, "a", "b", boom)
        self.assertNotIn(TOKEN, str(cm.exception))

    def test_url_encoded_token_masked(self):
        tok = "a/b+c"
        def boom(url, timeout=None):
            raise urllib.error.URLError(f"failed for {url}")
        with self.assertRaises(fetch_fx.FxFetchError) as cm:
            fetch_fx.fetch_pair("USD", tok, "a", "b", boom)
        self.assertNotIn("a%2Fb%2Bc", str(cm.exception))

    def test_cache_not_shrunk_without_force(self):
        with tempfile.TemporaryDirectory() as d:
            big = [[f"2020-01-{i:02d}", 1.0 + i / 100] for i in range(1, 21)]
            fetch_fx.write_cache(d, "USD", big, "2020-01-01", "2020-01-31")
            with self.assertRaises(fetch_fx.FxFetchError):
                fetch_fx.write_cache(d, "USD", big[10:], "2020-01-01",
                                     "2020-01-31")
            with open(os.path.join(d, "EURUSD.json")) as fh:
                self.assertEqual(len(json.load(fh)["rows"]), 20)
            fetch_fx.write_cache(d, "USD", big[10:], "2020-01-01",
                                 "2020-01-31", force=True)
            with open(os.path.join(d, "EURUSD.json")) as fh:
                self.assertEqual(len(json.load(fh)["rows"]), 10)
            self.assertEqual([f for f in os.listdir(d) if ".tmp" in f], [])

    def test_main_requires_token(self):
        old = os.environ.pop("EODHD_API_TOKEN", None)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(fetch_fx.main([]), 2)
        finally:
            if old is not None:
                os.environ["EODHD_API_TOKEN"] = old

    def test_main_writes_cache_and_reports_failure(self):
        old = os.environ.get("EODHD_API_TOKEN")
        os.environ["EODHD_API_TOKEN"] = TOKEN
        try:
            with tempfile.TemporaryDirectory() as d:
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    rc = fetch_fx.main(
                        ["--currencies", "AUD", "--cache", d,
                         "--from", "2020-01-01", "--to", "2020-01-31"],
                        _opener(_eod(("2020-01-02", 1.6))))
                self.assertEqual(rc, 0)
                with open(os.path.join(d, "EURAUD.json")) as fh:
                    doc = json.load(fh)
                self.assertEqual(doc["rows"], [["2020-01-02", 1.6]])
                self.assertNotIn(TOKEN, json.dumps(doc))
                with contextlib.redirect_stderr(io.StringIO()):
                    rc = fetch_fx.main(["--currencies", "AUD", "--cache", d],
                                       _opener([]))
                self.assertEqual(rc, 1)
        finally:
            if old is None:
                os.environ.pop("EODHD_API_TOKEN", None)
            else:
                os.environ["EODHD_API_TOKEN"] = old


def _cache(d, ccy, rows, fname=None, doc_ccy=None):
    doc = {"source": "EODHD", "currency": doc_ccy or ccy, "rows": rows}
    with open(os.path.join(d, fname or f"EUR{ccy}.json"), "w") as fh:
        json.dump(doc, fh)


def _conn():
    conn = sqlite3.connect(":memory:")
    conn.executescript(build_db.SCHEMA)
    return conn


class LoaderTest(unittest.TestCase):
    def test_load_and_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            _cache(d, "USD", [["2020-01-02", 1.12], ["2020-01-03", 1.11]])
            _cache(d, "AUD", [["2020-01-02", 1.6]])
            conn = _conn()
            self.assertEqual(build_db._load_fx_rates(conn, d), 3)
            self.assertEqual(build_db._load_fx_rates(conn, d), 3)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM fx_rates").fetchone()[0], 3)
            self.assertEqual(conn.execute(
                "SELECT per_eur FROM fx_rates WHERE currency='USD'"
                " AND date='2020-01-03'").fetchone()[0], 1.11)

    def test_missing_cache_warns_and_loads_nothing(self):
        with tempfile.TemporaryDirectory() as d, \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(build_db._load_fx_rates(_conn(), d), 0)
        self.assertIn("WARN", out.getvalue())

    def test_malformed_files_abort(self):
        cases = [
            ("bad rate", "USD", [["2020-01-02", 0]], {}),
            ("bool rate", "USD", [["2020-01-02", True]], {}),
            ("huge rate", "USD", [["2020-01-02", 1e9]], {}),
            ("compact date", "USD", [["20200102", 1.1]], {}),
            ("duplicate date", "USD",
             [["2020-01-02", 1.1], ["2020-01-02", 1.2]], {}),
            ("empty rows", "USD", [], {}),
            ("short row", "USD", [["2020-01-02"]], {}),
            ("neg rate", "USD", [["2020-01-02", -1.0]], {}),
            ("str rate", "USD", [["2020-01-02", "1.1"]], {}),
            ("bad date", "USD", [["02.01.2020", 1.1]], {}),
            ("name mismatch", "USD", [["2020-01-02", 1.1]],
             {"doc_ccy": "GBP"}),
        ]
        for label, ccy, rows, kw in cases:
            with tempfile.TemporaryDirectory() as d:
                _cache(d, ccy, rows, **kw)
                with self.assertRaises(ValueError, msg=label):
                    build_db._load_fx_rates(_conn(), d)

    def test_nan_and_corrupt_json_abort(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "EURUSD.json"), "w") as fh:
                fh.write('{"currency": "USD", "rows": [["2020-01-02", NaN]]}')
            with self.assertRaises(ValueError):
                build_db._load_fx_rates(_conn(), d)
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "EURUSD.json"), "w") as fh:
                fh.write("{not json")
            with self.assertRaises(ValueError) as cm:
                build_db._load_fx_rates(_conn(), d)
            self.assertIn("EURUSD.json", str(cm.exception))
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "EURUSD.json"), "w") as fh:
                json.dump({"currency": "USD"}, fh)  # no "rows"
            with self.assertRaises(ValueError):
                build_db._load_fx_rates(_conn(), d)

    def test_reload_replaces_stale_rows(self):
        with tempfile.TemporaryDirectory() as d:
            _cache(d, "USD", [["2020-01-02", 1.1], ["2020-01-03", 1.2]])
            conn = _conn()
            build_db._load_fx_rates(conn, d)
            _cache(d, "USD", [["2020-01-02", 1.3]])
            build_db._load_fx_rates(conn, d)
            self.assertEqual(
                conn.execute("SELECT date, per_eur FROM fx_rates").fetchall(),
                [("2020-01-02", 1.3)])

    def test_build_calls_loader(self):
        with tempfile.TemporaryDirectory() as d:
            _cache(d, "USD", [["2020-01-02", 1.1]])
            old_cache, old_arch = build_db.FX_CACHE, build_db.ARCHIVE
            build_db.FX_CACHE, build_db.ARCHIVE = d, d
            try:
                args = type("A", (), dict(limit=None, only="none",
                                          skip_resolution=True))()
                conn = sqlite3.connect(":memory:")
                with contextlib.redirect_stdout(io.StringIO()):
                    build_db._build(conn, args)
            finally:
                build_db.FX_CACHE, build_db.ARCHIVE = old_cache, old_arch
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM fx_rates").fetchone()[0], 1)

    def test_schema_rejects_nonpositive(self):
        for date, rate in (("2020-01-02", 0), ("2020-01-02", 1e9),
                           ("20200102", 1.1)):
            with self.assertRaises(sqlite3.IntegrityError, msg=(date, rate)):
                _conn().execute(
                    "INSERT INTO fx_rates VALUES ('USD', ?, ?, 'x')",
                    (date, rate))


if __name__ == "__main__":
    unittest.main()
