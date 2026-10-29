"""Unit tests for the search endpoint (in-memory SQLite fixture)."""
import os
import sqlite3
import tempfile
import unittest

from fastapi.testclient import TestClient

import main


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        self.tmp.close()
        conn = sqlite3.connect(self.tmp.name)
        conn.executescript("""
            CREATE TABLE wines (
                id INTEGER PRIMARY KEY, canonical_name TEXT,
                producer TEXT, region TEXT);
            CREATE TABLE providers (id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE auctions (id INTEGER PRIMARY KEY, provider_id INTEGER);
            CREATE TABLE lots (
                id INTEGER PRIMARY KEY, wine_ref_id INTEGER,
                auction_id INTEGER, lot_date TEXT, total_price REAL,
                realised_price REAL, currency TEXT);
            INSERT INTO wines VALUES
                (1, 'Château Montrose', 'Château Montrose', 'Saint-Estèphe'),
                (2, 'Montrose 2015', NULL, NULL),
                (3, 'Domaine Ravaut Corton-Bressandes', 'Domaine Ravaut',
                 'Corton');
            INSERT INTO providers VALUES (1, 'koppe');
            INSERT INTO auctions VALUES (1, 1);
            INSERT INTO lots VALUES
                (1, 1, 1, '2020-01-01', 100.0, 95.0, 'EUR'),
                (2, 1, 1, '2021-01-01', 120.0, 115.0, 'EUR'),
                (3, 1, 1, '2022-01-01', NULL, 140.0, 'EUR'),
                (4, 3, 1, '2020-06-01', 200.0, NULL, 'EUR');
        """)
        conn.commit()
        conn.close()
        main.DB_PATH = self.tmp.name
        self.client = TestClient(main.app)

    def tearDown(self):
        os.unlink(self.tmp.name)

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

    def test_search_requires_min_length(self):
        resp = self.client.get("/search", params={"q": "a"})
        self.assertEqual(resp.status_code, 422)

    def test_prices_returns_ordered_series(self):
        resp = self.client.get("/wines/1/prices")
        self.assertEqual(resp.status_code, 200)
        prices = resp.json()["prices"]
        self.assertEqual(len(prices), 3)
        self.assertEqual([p["lot_date"] for p in prices],
                         ["2020-01-01", "2021-01-01", "2022-01-01"])
        self.assertEqual(prices[0]["price"], 100.0)
        self.assertEqual(prices[0]["currency"], "EUR")

    def test_prices_falls_back_to_realised(self):
        resp = self.client.get("/wines/1/prices")
        prices = resp.json()["prices"]
        self.assertEqual(prices[2]["price"], 140.0)

    def test_prices_unknown_wine_empty(self):
        resp = self.client.get("/wines/9999/prices")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["prices"], [])

    def test_top_wines_ordered_by_lot_count(self):
        resp = self.client.get("/wines/top", params={"n": 10})
        self.assertEqual(resp.status_code, 200)
        results = resp.json()["results"]
        # wine 1 has 3 lots, wine 3 has 1; wine 2 has none and must be absent.
        self.assertEqual(results[0]["wine_id"], 1)
        self.assertEqual(results[0]["lot_count"], 3)
        self.assertNotIn(2, [r["wine_id"] for r in results])

    def test_top_wines_respects_n(self):
        resp = self.client.get("/wines/top", params={"n": 1})
        self.assertEqual(len(resp.json()["results"]), 1)


if __name__ == "__main__":
    unittest.main()
