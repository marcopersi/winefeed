"""load_aguttes (build_db.py) -- Review-fix regressions:

1. buyer_premium/realised_price must be derived whenever hammer/rate are
   known, even without a parsed vat_rate (only tax_amount/total_price,
   the TTC figures, actually need it) -- gating realised_price behind
   vat_rate too silently dropped price_per_bottle_eur for lots with a
   known premium but no parsed VAT text.
2. mixed_lot (set by the fetcher, see ingest/fetchers/aguttes.py) must
   survive into the ``lots`` row. bottle_size_dl is deliberately NOT
   this loader's job -- wine_resolution/bottle.py's shared
   parse_bottle_format (run by build_wines.py over every lot) derives
   it from the same raw_wine text, see that module's own tests.

Uses a real in-memory DB (build_db.SCHEMA) + a real ``Builder``, with
``_json_files``/``load_json`` monkeypatched to hand back fixture JSON
without touching the real archive -- the same insert path ``add_lot``
exercises in production, not a hand-rolled fake.
"""
import os
import sqlite3
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


def _load(auction, lots):
    conn = sqlite3.connect(":memory:")
    conn.executescript(build_db.SCHEMA)
    b = build_db.Builder(conn)
    data = {"auction": auction, "lots": lots}
    with mock.patch.object(build_db, "_json_files",
                           return_value=["fake/Aguttes/one.json"]), \
        mock.patch.object(build_db, "load_json", return_value=data):
        build_db.load_aguttes(b, limit=None)
    return conn


def _one_lot(conn):
    row = conn.execute(
        "SELECT hammer_price, buyer_premium, tax_amount, realised_price,"
        " total_price, price_source, mixed_lot"
        " FROM lots").fetchone()
    return dict(zip(
        ["hammer_price", "buyer_premium", "tax_amount", "realised_price",
         "total_price", "price_source", "mixed_lot"],
        row))


_AUCTION = {"id": "1", "name": "Sale", "date": "2026-01-01", "vat_rate": 0.2}


class HammerVatCompositionTests(unittest.TestCase):
    def test_full_vat_rate_known_computes_ttc_total(self):
        lot = {"hammer_price": 100.0, "premium_rate": 0.21, "sold": True}
        row = _one_lot(_load(_AUCTION, [lot]))
        self.assertEqual(row["buyer_premium"], 21.0)
        self.assertEqual(row["realised_price"], 121.0)
        self.assertEqual(row["tax_amount"], 4.2)
        self.assertEqual(row["total_price"], 125.2)
        self.assertEqual(row["price_source"], "DERIVED")

    def test_missing_vat_rate_still_derives_buyer_premium_and_realised_price(self):
        # Review finding: this must NOT fall back to NO_PREMIUM_POLICY --
        # the premium rate IS known, only VAT text failed to parse.
        auction = dict(_AUCTION, vat_rate=None)
        lot = {"hammer_price": 100.0, "premium_rate": 0.21, "sold": True}
        row = _one_lot(_load(auction, [lot]))
        self.assertEqual(row["buyer_premium"], 21.0)
        self.assertEqual(row["realised_price"], 121.0)
        self.assertEqual(row["price_source"], "DERIVED")
        self.assertIsNone(row["tax_amount"])
        self.assertIsNone(row["total_price"])

    def test_missing_premium_rate_derives_nothing(self):
        lot = {"hammer_price": 100.0, "premium_rate": None, "sold": True}
        row = _one_lot(_load(_AUCTION, [lot]))
        self.assertIsNone(row["buyer_premium"])
        self.assertIsNone(row["realised_price"])
        self.assertIsNone(row["price_source"])

    def test_mixed_lot_passes_through(self):
        lot = {"hammer_price": 100.0, "premium_rate": 0.21, "sold": True,
              "mixed_lot": 1}
        row = _one_lot(_load(_AUCTION, [lot]))
        self.assertEqual(row["mixed_lot"], 1)

    def test_mixed_lot_false_stays_null_not_zero(self):
        # add_lot's own convention elsewhere in this loader (the
        # HAMMER_PLUS_BUYERS_PREMIUM branch) is NULL, not 0, for "not
        # mixed" -- mirrored here for the same column.
        lot = {"hammer_price": 100.0, "premium_rate": 0.21, "sold": True,
              "mixed_lot": 0}
        row = _one_lot(_load(_AUCTION, [lot]))
        self.assertIsNone(row["mixed_lot"])


if __name__ == "__main__":
    unittest.main()
