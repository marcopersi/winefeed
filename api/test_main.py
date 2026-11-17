"""Unit tests for the search endpoint (in-memory SQLite fixture)."""
import os
import sqlite3
import tempfile
import unittest

from fastapi.testclient import TestClient

import main


class TestSearch(unittest.TestCase):
    def setUp(self):
        with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
            self.tmp_path = tmp.name
        conn = sqlite3.connect(self.tmp_path)
        conn.executescript("""
            CREATE TABLE wines (
                id INTEGER PRIMARY KEY, canonical_name TEXT,
                producer TEXT, region TEXT);
            CREATE TABLE providers (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE auctions (
                id INTEGER PRIMARY KEY, provider_id INTEGER, location TEXT);
            CREATE TABLE lots (
                id INTEGER PRIMARY KEY, wine_ref_id INTEGER,
                auction_id INTEGER, lot_date TEXT, total_price REAL,
                realised_price REAL, currency TEXT,
                lot_kind TEXT, vintage_status TEXT, vintage_final INTEGER,
                price_per_bottle_eur REAL);
            INSERT INTO wines VALUES
                (1, 'Château Montrose', 'Château Montrose', 'Saint-Estèphe'),
                (2, 'Montrose 2015', NULL, NULL),
                (3, 'Domaine Ravaut Corton-Bressandes', 'Domaine Ravaut',
                 'Corton'),
                (4, 'Pinot_Noir Reserve', NULL, NULL),
                (5, 'Pinots Noir Reserve', NULL, NULL),
                (6, 'A%B Edition', NULL, NULL),
                (7, 'AxyzB Edition', NULL, NULL),
                (8, 'Graubünden Pinot Noir', 'Weingut Donatsch',
                 'Graubünden');
            INSERT INTO providers VALUES (1, 'koppe');
            INSERT INTO auctions VALUES (1, 1, 'Köln');
            INSERT INTO lots VALUES
                -- wine 1: vintage 2020 is the most-traded (2 obs), 2021
                -- has 1 obs -- the default-vintage pick must prefer 2020.
                (1, 1, 1, '2020-01-01', 100.0, 95.0, 'EUR',
                 'SINGLE', 'STRUCTURED', 2020, 95.0),
                (2, 1, 1, '2020-06-01', 120.0, 115.0, 'EUR',
                 'SINGLE', 'STRUCTURED', 2020, 115.0),
                (3, 1, 1, '2021-01-01', NULL, 140.0, 'EUR',
                 'SINGLE', 'STRUCTURED', 2021, 140.0),
                -- wine 1: a MIXED lot and an unresolved-vintage lot --
                -- must NOT count as priceable observations anywhere.
                (4, 1, 1, '2022-01-01', 999.0, 999.0, 'EUR',
                 'MIXED', 'STRUCTURED', 2022, 999.0),
                (5, 1, 1, '2022-02-01', 999.0, 999.0, 'EUR',
                 'SINGLE', 'AMBIGUOUS', NULL, 999.0),
                -- wine 3: one priceable lot.
                (6, 3, 1, '2020-06-01', 200.0, NULL, 'EUR',
                 'SINGLE', 'STRUCTURED', 2019, 200.0);
        """)
        conn.commit()
        conn.close()
        main.DB_PATH = self.tmp_path
        self.client = TestClient(main.app)

    def tearDown(self):
        os.unlink(self.tmp_path)

    def test_search_returns_matches(self):
        resp = self.client.get("/search", params={"q": "montrose"})
        self.assertEqual(resp.status_code, 200)
        names = [r["canonical_name"] for r in resp.json()["results"]]
        self.assertIn("Château Montrose", names)

    def test_search_prefix_ordered_first(self):
        resp = self.client.get("/search", params={"q": "château"})
        results = resp.json()["results"]
        self.assertTrue(results[0]["canonical_name"].startswith("Château"))

    def test_search_reports_lot_count(self):
        resp = self.client.get("/search", params={"q": "montrose"})
        results = resp.json()["results"]
        for r in results:
            self.assertIn("lot_count", r)

    def test_search_lot_count_is_raw_row_count(self):
        # /search's lot_count is deliberately a cheap raw count (a
        # perf-critical, every-keystroke endpoint), unlike /wines/top's
        # priceable-only count below -- wine 1 has 5 rows total (3
        # priceable + 1 MIXED + 1 unresolved-vintage, see setUp).
        resp = self.client.get("/search", params={"q": "château montrose"})
        results = resp.json()["results"]
        self.assertEqual(results[0]["lot_count"], 5)

    def test_search_requires_min_length(self):
        resp = self.client.get("/search", params={"q": "a"})
        self.assertEqual(resp.status_code, 422)

    def test_search_case_insensitive_for_accented_letters(self):
        # Senior-review finding: SQLite's LIKE is ASCII-only case folding
        # by default, so a lowercase query would miss an uppercase
        # accented match ("GRAUBÜNDEN" vs "graubünden") without the
        # registered ulower() function.
        resp = self.client.get("/search", params={"q": "graubünden"})
        names = [r["canonical_name"] for r in resp.json()["results"]]
        self.assertIn("Graubünden Pinot Noir", names)

    def test_search_escapes_underscore_wildcard(self):
        # Senior-review finding: an unescaped "_" in the query is a SQL
        # LIKE single-character wildcard, so "Pinot_Noir" would also
        # match "Pinots Noir" (any char in place of "_"). It must match
        # only the literal underscore.
        resp = self.client.get("/search", params={"q": "Pinot_Noir"})
        names = [r["canonical_name"] for r in resp.json()["results"]]
        self.assertIn("Pinot_Noir Reserve", names)
        self.assertNotIn("Pinots Noir Reserve", names)

    def test_search_escapes_percent_wildcard(self):
        # Same issue for "%": unescaped, "A%B" matches "A", then anything,
        # then "B" -- it must match only the literal "%".
        resp = self.client.get("/search", params={"q": "A%B"})
        names = [r["canonical_name"] for r in resp.json()["results"]]
        self.assertIn("A%B Edition", names)
        self.assertNotIn("AxyzB Edition", names)

    def test_prices_default_vintage_is_most_traded(self):
        resp = self.client.get("/wines/1/prices")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["vintage"], 2020)
        prices = body["prices"]
        self.assertEqual(len(prices), 2)
        self.assertEqual([p["lot_date"] for p in prices],
                         ["2020-01-01", "2020-06-01"])
        self.assertEqual(prices[0]["price"], 95.0)
        self.assertEqual(prices[0]["currency"], "EUR")
        self.assertEqual(prices[0]["location"], "Köln")

    def test_prices_explicit_vintage_narrows_series(self):
        # Senior-review finding (critical): the chart must never mix
        # vintages into one series -- an explicit ?vintage= param must
        # return only that vintage's observations.
        resp = self.client.get("/wines/1/prices", params={"vintage": 2021})
        body = resp.json()
        self.assertEqual(body["vintage"], 2021)
        self.assertEqual([p["lot_date"] for p in body["prices"]],
                         ["2021-01-01"])

    def test_prices_unknown_wine_empty(self):
        resp = self.client.get("/wines/9999/prices")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["prices"], [])
        self.assertIsNone(resp.json()["vintage"])

    def test_vintages_lists_by_lot_count_desc(self):
        resp = self.client.get("/wines/1/vintages")
        self.assertEqual(resp.status_code, 200)
        vintages = resp.json()["vintages"]
        self.assertEqual(vintages,
                         [{"vintage": 2020, "lot_count": 2},
                          {"vintage": 2021, "lot_count": 1}])

    def test_top_wines_ordered_by_lot_count(self):
        resp = self.client.get("/wines/top", params={"n": 10})
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        # wine 1 has 3 priceable lots, wine 3 has 1; wine 2 has none and
        # must be absent.
        self.assertEqual(results[0]["wine_id"], 1)
        self.assertEqual(results[0]["lot_count"], 3)
        self.assertNotIn(2, [r["wine_id"] for r in results])

    def test_top_wines_respects_n(self):
        resp = self.client.get("/wines/top", params={"n": 1})
        self.assertEqual(len(resp.json()["results"]), 1)

    def test_unreachable_db_returns_503_not_raw_500(self):
        main.DB_PATH = "/no-such-directory-xyz/no.sqlite"
        resp = self.client.get("/search", params={"q": "montrose"})
        self.assertEqual(resp.status_code, 503)


if __name__ == "__main__":
    unittest.main()
