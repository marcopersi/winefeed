"""_check_duplicate_lot_numbers: distinguishes a real load-duplication bug
(same auction_id/lot_no/wine/vintage/quantity/region/condition_text/
hammer_price seen more than once -- a loader double-loading the same lot)
from a genuinely different row sharing a reused lot_no -- either a source
data error (the known xlsx case: lot 299 on 19.10.2013, "Contador" vs
"Giusto di Notri", same price) or, for langtons, that house's own
convention of grouping several distinct sub-lots under one lot number.
Only the first is a build-breaking bug.
"""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


def _conn_with_lots(rows, vintage=None, quantity=None, region=None,
                     condition_text=None):
    """rows: (lot_no, wine, hammer) tuples. The other fields are optional
    parallel lists (same length as rows) for tests that need to vary a
    specific field."""
    conn = sqlite3.connect(":memory:")
    conn.executescript(build_db.SCHEMA)
    conn.execute("INSERT INTO providers(id, name) VALUES (1, 'p')")
    conn.execute(
        "INSERT INTO auctions(id, provider_id, auction_id) VALUES (1, 1, 'a')")
    for i, (lot_no, wine, hammer) in enumerate(rows):
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, vintage, quantity,"
            " region, condition_text, hammer_price)"
            " VALUES (1, ?, ?, ?, ?, ?, ?, ?)",
            (lot_no, wine, vintage[i] if vintage else None,
             quantity[i] if quantity else None,
             region[i] if region else None,
             condition_text[i] if condition_text else None, hammer))
    return conn


class DuplicateLotGateTest(unittest.TestCase):
    def test_no_duplicates(self):
        conn = _conn_with_lots([("1", "A", 100.0), ("2", "B", 200.0)])
        self.assertEqual(build_db._check_duplicate_lot_numbers(conn), (0, 0))

    def test_true_load_duplicate(self):
        """Same lot_no, same wine, same price twice -- a loader reading
        the same real lot from two files (or the same file twice)."""
        conn = _conn_with_lots(
            [("1", "A", 100.0), ("1", "A", 100.0), ("2", "B", 200.0)])
        load_dups, source_dups = build_db._check_duplicate_lot_numbers(conn)
        self.assertEqual(load_dups, 1)
        self.assertEqual(source_dups, 0)

    def test_source_data_error_is_not_a_load_duplicate(self):
        """Same lot_no, but two genuinely different wines -- a reused
        lot number in the source itself (confirmed real case: Wermuth
        xlsx lot 299 on 19.10.2013), not a loader bug."""
        conn = _conn_with_lots(
            [("299", "Contador", 130.0), ("299", "Giusto di Notri", 130.0)])
        load_dups, source_dups = build_db._check_duplicate_lot_numbers(conn)
        self.assertEqual(load_dups, 0)
        self.assertEqual(source_dups, 1)

    def test_same_lot_no_different_vintage_is_not_a_duplicate(self):
        """Confirmed real case: langtons sale 1737 lot "1" -- three
        genuinely different lots (1993/1994/1995 vintages of the same
        wine) share one lot number AND the same winning bid. wine+price
        alone would flag all three as a load bug; vintage tells them
        apart."""
        conn = _conn_with_lots(
            [("1", "Cape Mentelle Zinfandel", 37.0)] * 3,
            vintage=[1993, 1994, 1995])
        load_dups, source_dups = build_db._check_duplicate_lot_numbers(conn)
        self.assertEqual(load_dups, 0)
        self.assertEqual(source_dups, 2)

    def test_same_lot_no_different_quantity_is_not_a_duplicate(self):
        """Confirmed real case: langtons sale 1746 lot "1197" -- one lot
        split into sub-lots of 10 bottles and 2 "Stained Labels" bottles,
        same wine/vintage/price, told apart only by quantity."""
        conn = _conn_with_lots(
            [("1197", "Chateau Cos d'Estournel", 200.0)] * 2,
            vintage=[1990, 1990], quantity=[10, 2])
        load_dups, source_dups = build_db._check_duplicate_lot_numbers(conn)
        self.assertEqual(load_dups, 0)
        self.assertEqual(source_dups, 1)

    def test_same_lot_no_different_region_is_not_a_duplicate(self):
        """Confirmed real case: langtons sale 1766 lot "2895" -- a mixed
        DRC lot with six different appellations (Echezeaux, La Tache, ...)
        sharing one lot number, vintage and price."""
        conn = _conn_with_lots(
            [("2895", "DOMAINE DE LA ROMANEE-CONTI", 901.0)] * 2,
            vintage=[1995, 1995], quantity=[3, 3],
            region=["Echezeaux", "La Tache"])
        load_dups, source_dups = build_db._check_duplicate_lot_numbers(conn)
        self.assertEqual(load_dups, 0)
        self.assertEqual(source_dups, 1)

    def test_same_lot_no_different_condition_text_is_not_a_duplicate(self):
        """Confirmed real case: langtons sale 1763 lot "838" -- four
        ROCKFORD Black Sparkling Shiraz sub-lots, same wine/vintage/
        quantity/price, told apart only by disgorgement date in the
        notes (condition_text)."""
        conn = _conn_with_lots(
            [("838", "ROCKFORD Black Sparkling Shiraz", 70.0)] * 2,
            quantity=[1, 1],
            condition_text=["disgorged September 1998",
                             "Disgorged August 1999"])
        load_dups, source_dups = build_db._check_duplicate_lot_numbers(conn)
        self.assertEqual(load_dups, 0)
        self.assertEqual(source_dups, 1)

    def test_validate_gates_warns_but_does_not_yet_raise_on_load_duplicate(
            self):
        """Not a hard gate YET: other houses still carry this same bug
        in smaller numbers, so raising here would break every build
        until all of them are cleaned up too -- separate, not-yet-
        scheduled work. Promote to a hard gate once that lands."""
        conn = _conn_with_lots([("1", "A", 100.0), ("1", "A", 100.0)])
        build_db._validate_gates(conn)  # must not raise (for now)

    def test_validate_gates_does_not_raise_on_source_data_error(self):
        """The known pre-existing xlsx class must not block every future
        build until someone fixes the source data."""
        conn = _conn_with_lots(
            [("299", "Contador", 130.0), ("299", "Giusto di Notri", 130.0)])
        build_db._validate_gates(conn)  # must not raise


if __name__ == "__main__":
    unittest.main()
