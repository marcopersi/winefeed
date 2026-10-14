"""Loader roundtrip: a normalized fetcher output must survive its loader.

Feeds the canonical ``{auction, lots}`` shape that each fetcher emits into its
matching ``load_*`` function and asserts the loader actually reads the fields
(no silent NULLs). This guards the fetcher<->loader field-name contract.
"""
import json
import os
import sqlite3
import tempfile
import unittest

import build_db


def _run_loader(house_dir, filename, data, loader_name):
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, house_dir), exist_ok=True)
        with open(os.path.join(d, house_dir, filename), "w",
                  encoding="utf-8") as fh:
            json.dump(data, fh)
        conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        old = build_db.ARCHIVE
        build_db.ARCHIVE = d
        try:
            getattr(build_db, loader_name)(builder, None)
        finally:
            build_db.ARCHIVE = old
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
        hammer = conn.execute(
            "SELECT COUNT(*) FROM lots WHERE hammer_price IS NOT NULL"
        ).fetchone()[0]
        wine = conn.execute(
            "SELECT COUNT(*) FROM lots WHERE wine IS NOT NULL"
        ).fetchone()[0]
        conn.close()
        return count, hammer, wine


class TestLoaderRoundtrip(unittest.TestCase):
    def test_apply_premium_policy(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "Koppe 1", None, "EUR",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x",
                               "hammer_price": 100.0, "price_basis": "HAMMER",
                               "currency": "EUR"})
        build_db._apply_premium_policy(conn)
        row = conn.execute(
            "SELECT buyer_premium, fees, total_price, price_source FROM lots"
        ).fetchone()
        self.assertEqual(row, (10.0, 5.0, 115.0, "DERIVED"))
        conn.close()

    def test_apply_tax(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "Koppe 1", None, "EUR",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x",
                               "hammer_price": 100.0, "price_basis": "HAMMER",
                               "currency": "EUR"})
        build_db._apply_premium_policy(conn)
        build_db._apply_tax(conn)
        row = conn.execute(
            "SELECT buyer_premium, fees, tax_amount, total_price, price_source"
            " FROM lots").fetchone()
        self.assertEqual(row, (10.0, 5.0, 1.9, 116.9, "DERIVED"))
        conn.close()

    def test_fill_lot_date(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "Koppe 1", "2026-01-31",
                                   "EUR", "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x",
                               "lot_date": "2026-01-30"})
        builder.add_lot(a_id, {"lot_no": "2", "wine": "y"})
        build_db._fill_lot_date(conn)
        rows = conn.execute(
            "SELECT lot_no, lot_date FROM lots ORDER BY lot_no").fetchall()
        self.assertEqual(rows, [("1", "2026-01-30"), ("2", "2026-01-31")])
        conn.close()

    def test_langtons(self):
        data = {"auction": {"id": "8212", "name": "Unreserved", "date": None},
                "lots": [{"lot": "1", "wine": "Penfolds Grange",
                          "region": "South Australia", "classification": None,
                          "vintage": "2019", "quantity": "1",
                          "winning_bid": 850.0, "currency": "AUD",
                          "notes": None}]}
        count, hammer, wine = _run_loader(
            "Langtons", "8212.json", data, "load_langtons")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_winefields(self):
        data = {"auction": {"auction_id": "1-AO56VE", "title": "WF83",
                            "time_start": "2026-09-22T16:00:00Z"},
                "lots": [{"lot_no": 1, "title": "Marsannay Rouge",
                          "producer": None, "quantity": 6, "size": None,
                          "estimate_low": "160.00", "estimate_high": "220.00",
                          "hammer": "200.00", "status": "sold",
                          "is_mixed_lot": False, "condition": None,
                          "currency": "EUR"}]}
        count, hammer, wine = _run_loader(
            "Winefields", "1-AO56VE.json", data, "load_winefields")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_dorotheum(self):
        data = {"auction": {"id": "127195", "name": None, "date": None},
                "lots": [{"lot_nr": "139-1", "name": "Château Mouton",
                          "estimate": 800.0, "realized_price": 400.0,
                          "sold": 1, "currency": "EUR",
                          "description": None}]}
        count, hammer, wine = _run_loader(
            "Dorotheum", "127195.json", data, "load_dorotheum")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_pandolfini(self):
        data = {"auction": {"id": "1448", "name": "Smartwine",
                            "date": "2026-04-08"},
                "lots": [{"lot_nr": 1, "name": "Ruinart",
                          "estimate_low": None, "estimate_high": None,
                          "sold_price": {"class": "venduto", "value": 20},
                          "description": "Champagne"}]}
        count, _hammer, wine = _run_loader(
            "Pandolfini", "1448.json", data, "load_pandolfini")
        self.assertEqual((count, wine), (1, 1))

    def test_sothebys(self):
        data = {"auction": {"auction_id": "d19bbb8e-71c4-42b9-aba5-366d311806a9",
                            "title": "Live from The Macallan Estate",
                            "dates": "2026-10-09T14:57:00Z",
                            "currency": "GBP", "location": "London"},
                "lots": [{"lot_number": "1", "title": "The Macallan 42.6",
                          "estimate_low": "60000", "estimate_high": "100000",
                          "hammer_price": "140000", "final_price": 175000.0,
                          "sold": 1, "currency": "GBP"}]}
        count, hammer, wine = _run_loader(
            "Sothebys", "l26722.json", data, "load_sothebys")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_finarte(self):
        data = {"auction": {"slug": "fine-wines-16", "name": None,
                            "date": None},
                "lots": [{"lot_nr": "1", "name": "Gaja (1 BT)",
                          "region": "Barbaresco", "vintage": "1981",
                          "estimate_min": "180", "estimate_max": "220",
                          "hammer_price": 221.4, "sold": 1,
                          "currency": "EUR", "vat_regime": "RF15"}]}
        count, hammer, wine = _run_loader(
            "Finarte", "16.json", data, "load_finarte")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_beschcannes(self):
        data = {"auction": {"id": "408", "slug": "408-x", "date": None,
                            "currency": "EUR", "price_basis": "HAMMER"},
                "lots": [{"lot_no": "401", "appellation": "Dom Perignon",
                          "vintage": "1973", "estimate": [1000.0, 1500.0],
                          "adjuge": 2650.0, "description": "1 Bouteille",
                          "remarks": None}]}
        count, hammer, wine = _run_loader(
            "BeschCannes", "auction-408.json", data, "load_beschcannes")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_christies(self):
        data = {"auction": {"event_id": "31122", "title": "Henry Tang",
                            "year": 2026, "month": 10,
                            "landing_url": "https://www.christies.com/en/"
                                           "auction/auction-31122",
                            "location": "HongKong"},
                "lots": [{"lot_number": "1",
                          "title": "Château Lafite Rothschild 1953",
                          "estimate_low": 70000.0, "estimate_high": 100000.0,
                          "price_realised": 118750.0, "lot_withdrawn": False,
                          "currency": "HKD", "description": "1 Magnum",
                          "url": "https://www.christies.com/en/lot/lot-6604342"}]}
        count, hammer, wine = _run_loader(
            "Christies", "31122.json", data, "load_christies")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_koppe(self):
        data = {"auction": {"id": "10", "name": "Koppe 10", "date": None},
                "lots": [{"lot_no": "1", "name": "Chateau Haut-Brion",
                          "region": "Pessac-Leognan", "vintage": "1998",
                          "color": "Rot", "bottle_size": "6,0 l",
                          "format": ["1 Imperial"],
                          "hammer_price": 6000.0}]}
        count, hammer, wine = _run_loader(
            "Koppe", "10.json", data, "load_koppe")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_weinboerse(self):
        data = {"auction": {"id": "627", "name": "eAuktion 116",
                            "date": "2026-01-31", "currency": "CHF"},
                "lots": [{"lot_no": "1", "wine": "Barolo 2015",
                          "vintage": "2015", "estimate_low": 20.0,
                          "estimate_high": 40.0, "hammer_price": 34.0,
                          "sold": 1, "currency": "CHF"}]}
        count, hammer, wine = _run_loader(
            "weinboerse", "627.json", data, "load_weinboerse")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_dobiaschofsky(self):
        data = {"auction": {"id": "wein", "name": None, "date": None},
                "lots": [{"lot_nr": "12550", "name": "Domaine de la Romanee",
                          "vintage": "1986", "estimate_chf": None,
                          "hammer_chf": 10000.0,
                          "description": "Romanee Conti"}]}
        count, hammer, wine = _run_loader(
            "Dobiaschofsky", "auktion-wein.json", data, "load_dobiaschofsky")
        self.assertEqual((count, hammer, wine), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
