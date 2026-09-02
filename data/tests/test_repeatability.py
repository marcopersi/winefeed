import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from build_db import SCHEMA  # noqa: E402
from build_wines import run as resolve_wines  # noqa: E402

FIXTURE_LOTS = [
    # (provider, auction_id, lot_no, wine, producer, region, vintage)
    ("fx", "a1", "1", "Château Margaux 2005", None, "Margaux", None),
    ("fx", "a1", "2", "Chateau Margaux 2000", None, "Margaux", None),
    ("fx", "a2", "1", "Pétrus 2009", None, "Pomerol", None),
    ("fx", "a2", "2", "Petrus", None, "Pomerol", 2009),
    ("fx", "a2", "3", "Château Petrus", None, "Pomerol", None),
    ("fx", "a3", "1", "Mixed lot Bordeaux", None, None, None),
]


def build_fixture():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    pid = conn.execute(
        "INSERT INTO providers(name) VALUES ('fx')").lastrowid
    auction_ids = {}
    for _, auction_id, _, _, _, _, _ in FIXTURE_LOTS:
        if auction_id not in auction_ids:
            auction_ids[auction_id] = conn.execute(
                "INSERT INTO auctions(provider_id, auction_id, title,"
                " auction_date) VALUES (?,?,?,?)",
                (pid, auction_id, auction_id, "2010-01-01")).lastrowid
    for _, auction_id, lot_no, wine, producer, region, vintage in \
            FIXTURE_LOTS:
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, raw_wine, wine, producer,"
            " region, vintage, raw_vintage) VALUES (?,?,?,?,?,?,?,?)",
            (auction_ids[auction_id], lot_no, wine, wine, producer, region,
             vintage, str(vintage) if vintage else None))
    conn.commit()
    resolve_wines(conn)
    return conn


def snapshot(conn):
    return {
        "wines": sorted(conn.execute(
            "SELECT stable_key, canonical_name FROM wines").fetchall()),
        "aliases": sorted(conn.execute(
            "SELECT alias_key, resolution_status FROM wine_alias_resolutions"
            " ORDER BY alias_key").fetchall()),
        "refs": conn.execute(
            "SELECT COALESCE(wine_ref_id, -1) FROM lots ORDER BY id"
        ).fetchall(),
    }


class TestRepeatability(unittest.TestCase):
    def test_two_builds_identical(self):
        c1 = build_fixture()
        c2 = build_fixture()
        self.assertEqual(snapshot(c1), snapshot(c2))

    def test_margaux_merged(self):
        conn = build_fixture()
        cnt = conn.execute(
            "SELECT count(*) FROM wines WHERE canonical_key="
            "'chateau margaux'").fetchone()[0]
        self.assertEqual(cnt, 1)

    def test_petrus_merged_via_override(self):
        conn = build_fixture()
        # Petrus + Pétrus merge via diacritics; Château Petrus via override.
        names = [r[0] for r in conn.execute(
            "SELECT canonical_name FROM wines WHERE canonical_key='petrus'")]
        self.assertIn("Pétrus", names)

    def test_mixed_lot_no_wine_ref(self):
        conn = build_fixture()
        bad = conn.execute(
            "SELECT count(*) FROM lots WHERE lot_kind='MIXED'"
            " AND wine_ref_id IS NOT NULL").fetchone()[0]
        self.assertEqual(bad, 0)


if __name__ == "__main__":
    unittest.main()
