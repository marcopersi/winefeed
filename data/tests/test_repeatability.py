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
    ("fx", "a4", "1", "Sassicaia 2015", None, "Toscana", None),
    ("fx", "a4", "2", "Sassicaia 2015", "Tenuta San Guido", "Toscana", None),
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
        # §4.2/4.3: the producer-index + fuzzy match splits "Château
        # Margaux" into producer="Château Margaux" / wine="Margaux" (the
        # pure wine name, per the Wine.name/Wine.producer model in §0 of
        # wine-pipeline-v2.md), so both raw spellings merge under
        # canonical_key='margaux' with producer_key='chateau margaux'.
        cnt = conn.execute(
            "SELECT count(*) FROM wines WHERE canonical_key='margaux'"
            " AND producer_key='chateau margaux'").fetchone()[0]
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

    def test_single_lots_backfilled(self):
        # Regression gate for the exact "stiller Datenverlust" §4.1 exists
        # to prevent: a SINGLE lot that was correctly resolved into
        # wine_alias_resolutions must come back out with a wine_ref_id.
        # This caught a real bug where producer/wine matching (§4.2/4.3)
        # rewrote the in-memory alias but never wrote it back to
        # lots.wine/lots.producer, so _backfill_wine_ref looked up a key
        # the resolutions table never had — every matched lot lost its
        # wine_ref_id silently.
        conn = build_fixture()
        missing = conn.execute(
            "SELECT count(*) FROM lots WHERE lot_kind='SINGLE'"
            " AND wine_ref_id IS NULL").fetchone()[0]
        self.assertEqual(missing, 0)

    def test_producer_less_sibling_absorbed_into_known_producer(self):
        # Confirmed real case (live DB): "Sassicaia" with producer=NULL and
        # "Sassicaia" with producer="Tenuta San Guido" used to resolve into
        # two separate wines rows for the same real wine. §4.1's own
        # AMBIGUOUS-splitting already ignores "" when checking for a
        # producer conflict; absorbing the producer-less sibling into the
        # one known-producer group (instead of resolving it on its own)
        # merges them into a single wines row.
        conn = build_fixture()
        wine_ids = {r[0] for r in conn.execute(
            "SELECT wine_ref_id FROM lots WHERE auction_id ="
            " (SELECT id FROM auctions WHERE auction_id='a4')")}
        self.assertEqual(len(wine_ids), 1)
        self.assertNotIn(None, wine_ids)
        producer = conn.execute(
            "SELECT producer FROM wines WHERE id = ?",
            (next(iter(wine_ids)),)).fetchone()[0]
        self.assertEqual(producer, "Tenuta San Guido")


if __name__ == "__main__":
    unittest.main()
