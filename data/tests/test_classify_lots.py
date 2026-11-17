"""_classify_lots (build_wines.py): #93 fix regression tests.

Both new rules close a gap in the SAME failure mode: a bundled, multi-wine
catalog lot arrives as a single raw row (one source_lot_key, one row), so
the sibling-comparison checks in classify_group() (distinct wine keys,
distinct vintages) never see it -- only a text-only pass across every
not-yet-classified row can catch it.
"""
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402
import build_wines  # noqa: E402


def _conn_with_lots(wines, source_lot_keys=None, descriptions=None,
                     mixed_lots=None):
    conn = sqlite3.connect(":memory:")
    conn.executescript(build_db.SCHEMA)
    conn.execute("INSERT INTO providers(id, name) VALUES (1, 'p')")
    conn.execute(
        "INSERT INTO auctions(id, provider_id, auction_id) VALUES (1, 1, 'a')")
    for i, wine in enumerate(wines):
        sk = source_lot_keys[i] if source_lot_keys else f"a-{i}"
        desc = descriptions[i] if descriptions else None
        mixed_lot = mixed_lots[i] if mixed_lots else None
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, source_lot_key, wine,"
            " description, mixed_lot) VALUES (1, ?, ?, ?, ?, ?)",
            (str(i), sk, wine, desc, mixed_lot))
    conn.commit()
    return conn


def _kind(conn, wine):
    return conn.execute(
        "SELECT lot_kind, mixed_reason FROM lots WHERE wine=?",
        (wine,)).fetchone()


class TestClassifyLotsKeywordEvidence(unittest.TestCase):
    def test_mixed_lot_single_row_becomes_mixed(self):
        wine = "Mixed lot Bordeaux 1975-1980"
        conn = _conn_with_lots([wine])
        build_wines._classify_lots(conn)
        kind, reason = _kind(conn, wine)
        self.assertEqual(kind, "MIXED")
        self.assertEqual(reason, "keyword-evidence")

    def test_genuine_single_wine_unaffected(self):
        wine = "Château Margaux 2005"
        conn = _conn_with_lots([wine])
        build_wines._classify_lots(conn)
        kind, _ = _kind(conn, wine)
        self.assertEqual(kind, "SINGLE")

    def test_tasting_note_mixed_fruit_not_mixed(self):
        # Senior-review finding: a bare "mixed" would also fire on
        # ordinary tasting-note language ("mixed fruit", "mixed spices")
        # for a genuinely single wine -- matches_keyword() deliberately
        # stays scoped to "mixed lot"/"mixed case"/"assortment"/
        # "selection", not the bare word.
        wine = "Château Margaux 2005"
        conn = _conn_with_lots(
            [wine], descriptions=["a nice balance of mixed fruit"])
        build_wines._classify_lots(conn)
        kind, _ = _kind(conn, wine)
        self.assertEqual(kind, "SINGLE")

    def test_intermixed_substring_not_mixed(self):
        # SQL LIKE '%mixed%' is only a pre-filter with no word boundary
        # and would also match "intermixed" inside a tasting note -- the
        # real decision must go through the \b-bounded matches_keyword()
        # regex instead.
        wine = "Château Margaux 2005, notes intermixed with roasted herbs"
        conn = _conn_with_lots([wine])
        build_wines._classify_lots(conn)
        kind, _ = _kind(conn, wine)
        self.assertEqual(kind, "SINGLE")

    def test_propagates_to_sibling_row_sharing_source_lot_key(self):
        # Senior-review finding: a text-only rule must not classify one
        # row of a multi-row source_lot_key group in isolation -- the
        # sibling would then see count==1 in the group-classification
        # query below and fall through to the SINGLE fallback instead of
        # sharing the group's MIXED verdict.
        wine_a, wine_b = "Mixed lot Bordeaux", "Château Latour 1990"
        conn = _conn_with_lots([wine_a, wine_b],
                               source_lot_keys=["shared", "shared"])
        build_wines._classify_lots(conn)
        kind_a, reason_a = _kind(conn, wine_a)
        kind_b, reason_b = _kind(conn, wine_b)
        self.assertEqual(kind_a, "MIXED")
        self.assertEqual(kind_b, "MIXED")
        self.assertEqual(reason_a, reason_b)


class TestClassifyLotsProviderFlagPropagation(unittest.TestCase):
    def test_propagates_to_sibling_row_sharing_source_lot_key(self):
        # Senior-review finding, reproduced live: the provider mixed_lot
        # flag can land on only one row of a bundled lot; its sibling
        # (mixed_lot=0/NULL) must inherit MIXED too, not fall through to
        # the group-classification's count==1 case and end up SINGLE.
        wine_a, wine_b = "Château Margaux 2005", "Château Latour 1990"
        conn = _conn_with_lots([wine_a, wine_b],
                               source_lot_keys=["shared", "shared"],
                               mixed_lots=[1, 0])
        build_wines._classify_lots(conn)
        kind_a, reason_a = _kind(conn, wine_a)
        kind_b, reason_b = _kind(conn, wine_b)
        self.assertEqual(kind_a, "MIXED")
        self.assertEqual(kind_b, "MIXED")
        self.assertEqual(reason_a, reason_b)


class TestClassifyLotsRepeatedVintageSeparator(unittest.TestCase):
    def test_bundled_catalog_lot_becomes_mixed(self):
        wine = ("Château Palmer--Vintage 1991. C.B. (6) Château L'Angélus"
                "--Vintage 1992. C.B. (6)")
        conn = _conn_with_lots([wine])
        build_wines._classify_lots(conn)
        kind, reason = _kind(conn, wine)
        self.assertEqual(kind, "MIXED")
        self.assertEqual(reason, "repeated-vintage-separator")

    def test_single_vintage_separator_stays_single(self):
        wine = "Château Latour--Vintage 1990 (6)"
        conn = _conn_with_lots([wine])
        build_wines._classify_lots(conn)
        kind, _ = _kind(conn, wine)
        self.assertEqual(kind, "SINGLE")

    def test_propagates_to_sibling_row_sharing_source_lot_key(self):
        wine_a = ("Château Palmer--Vintage 1991. C.B. (6) Château L'Angélus"
                  "--Vintage 1992. C.B. (6)")
        wine_b = "Château Latour 1990"
        conn = _conn_with_lots([wine_a, wine_b],
                               source_lot_keys=["shared", "shared"])
        build_wines._classify_lots(conn)
        kind_a, reason_a = _kind(conn, wine_a)
        kind_b, reason_b = _kind(conn, wine_b)
        self.assertEqual(kind_a, "MIXED")
        self.assertEqual(kind_b, "MIXED")
        self.assertEqual(reason_a, reason_b)


if __name__ == "__main__":
    unittest.main()
