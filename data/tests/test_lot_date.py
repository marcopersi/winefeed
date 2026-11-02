"""lot_date normalization: dd.mm.yyyy -> ISO, then backfill from auction_date."""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


def _conn(rows, auction_date="2020-06-01"):
    conn = sqlite3.connect(":memory:")
    conn.executescript(build_db.SCHEMA)
    conn.execute("INSERT INTO providers(id, name) VALUES (1, 'p')")
    conn.execute(
        "INSERT INTO auctions(id, provider_id, auction_id, auction_date)"
        " VALUES (1, 1, 'a', ?)", (auction_date,))
    for i, d in enumerate(rows):
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, lot_date) VALUES (1, ?, ?)",
            (str(i), d))
    return conn


def _dates(conn):
    return [r[0] for r in conn.execute("SELECT lot_date FROM lots ORDER BY id")]


class LotDateTest(unittest.TestCase):
    def test_dmy_converted(self):
        conn = _conn(["04.05.2002", "29.02.2020", "01.01.1900"])
        build_db._fill_lot_date(conn)
        self.assertEqual(_dates(conn),
                         ["2002-05-04", "2020-02-29", "1900-01-01"])

    def test_iso_untouched(self):
        conn = _conn(["2026-08-18"])
        build_db._fill_lot_date(conn)
        self.assertEqual(_dates(conn), ["2026-08-18"])

    def test_invalid_left_and_counted(self):
        conn = _conn(["31.02.2020", "29.02.2019"])
        converted, invalid = build_db._normalize_lot_date(conn)
        self.assertEqual((converted, invalid), (0, 2))
        self.assertEqual(_dates(conn), ["31.02.2020", "29.02.2019"])

    def test_null_backfilled_from_auction(self):
        conn = _conn([None])
        build_db._fill_lot_date(conn)
        self.assertEqual(_dates(conn), ["2020-06-01"])

    def test_existing_not_overwritten(self):
        conn = _conn(["2019-01-01"])
        build_db._fill_lot_date(conn)
        self.assertEqual(_dates(conn), ["2019-01-01"])

    def test_idempotent(self):
        conn = _conn(["04.05.2002", None])
        build_db._fill_lot_date(conn)
        first = _dates(conn)
        build_db._fill_lot_date(conn)
        self.assertEqual(_dates(conn), first)


if __name__ == "__main__":
    unittest.main()
