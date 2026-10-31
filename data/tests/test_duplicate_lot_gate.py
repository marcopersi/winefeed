"""_check_duplicate_lot_numbers: distinguishes a real load-duplication bug
(same auction_id/lot_no/wine/hammer_price seen more than once -- a loader
double-loading the same lot) from a source data error (same lot_no reused
for two genuinely different wines, e.g. the known xlsx case: lot 299 on
19.10.2013, "Contador" vs "Giusto di Notri", same price) -- only the first
is a build-breaking bug.
"""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


def _conn_with_lots(rows):
    conn = sqlite3.connect(":memory:")
    conn.executescript(build_db.SCHEMA)
    conn.execute("INSERT INTO providers(id, name) VALUES (1, 'p')")
    conn.execute(
        "INSERT INTO auctions(id, provider_id, auction_id) VALUES (1, 1, 'a')")
    for lot_no, wine, hammer in rows:
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, hammer_price)"
            " VALUES (1, ?, ?, ?)", (lot_no, wine, hammer))
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

    def test_validate_gates_warns_but_does_not_yet_raise_on_load_duplicate(
            self):
        """Not a hard gate YET: 8 houses besides christies still carry
        this same bug in smaller numbers, so raising here would break
        every build until all of them are cleaned up too -- separate,
        not-yet-scheduled work. Promote to a hard gate once that lands."""
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
