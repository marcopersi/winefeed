"""run_idealwine_delta.py's archive-writing helper: groups flat
new_adjudications() records by (product_id, vintage) into the per-product
file shape load_idealwine already reads from IDealwine_normalized/_delta/.
"""
import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import build_db  # noqa: E402
from run_idealwine_delta import _archive_new_adjudications  # noqa: E402

REC_A1 = {
    "product_id": 197, "vintage": 2022, "wine": "Château Croizet Bages",
    "estate": "Château Croizet Bages", "region": "Bordeaux",
    "appellation": "Pauillac", "color": "RED", "classification": None,
    "sold_at": "2026-08-05T10:00:00+00:00", "format": "BOUTEILLE",
    "number_of_bottles": 1, "hammer_lot_eur": 25.0,
    "hammer_per_bottle_eur": 25.0, "total_per_bottle_eur": 31.46,
    "price_basis": "HAMMER", "code": "2800001",
}
REC_A2 = dict(REC_A1, sold_at="2026-08-10T10:00:00+00:00", code="2800002")
REC_B = {
    "product_id": 300, "vintage": 2019, "wine": "Some Other Wine",
    "estate": "Domaine Other", "region": "Bourgogne",
    "appellation": "Beaune", "color": "RED", "classification": None,
    "sold_at": "2026-08-07T10:00:00+00:00", "format": "BOUTEILLE",
    "number_of_bottles": 6, "hammer_lot_eur": 300.0,
    "hammer_per_bottle_eur": 50.0, "total_per_bottle_eur": 62.0,
    "price_basis": "HAMMER", "code": "2800003",
}


class ArchiveNewAdjudicationsTest(unittest.TestCase):
    def test_groups_by_product_and_vintage(self):
        with tempfile.TemporaryDirectory() as d:
            written = _archive_new_adjudications(d, [REC_A1, REC_A2, REC_B])
            self.assertEqual(written, 2)
            out_dir = os.path.join(d, "IDealwine_normalized", "_delta")
            files = sorted(os.listdir(out_dir))
            self.assertEqual(len(files), 2)

            a_file = next(f for f in files if f.startswith("197-2022"))
            with open(os.path.join(out_dir, a_file), encoding="utf-8") as fh:
                doc = json.load(fh)
            self.assertEqual(doc["product_id"], 197)
            self.assertEqual(doc["vintage"], 2022)
            self.assertEqual(doc["wine"], "Château Croizet Bages")
            self.assertEqual(doc["region"], "Bordeaux")
            self.assertEqual(len(doc["adjudications"]), 2)
            codes = {a["code"] for a in doc["adjudications"]}
            self.assertEqual(codes, {"2800001", "2800002"})

            b_file = next(f for f in files if f.startswith("300-2019"))
            with open(os.path.join(out_dir, b_file), encoding="utf-8") as fh:
                doc_b = json.load(fh)
            self.assertEqual(len(doc_b["adjudications"]), 1)
            self.assertEqual(doc_b["adjudications"][0]["code"], "2800003")

    def test_adjudication_entries_drop_wine_identity_fields(self):
        """The per-adjudication dict must only carry adjudication fields --
        wine/estate/region etc. belong at the file's top level, once, not
        repeated on every adjudication (matches the existing archive's own
        per-product file shape)."""
        with tempfile.TemporaryDirectory() as d:
            _archive_new_adjudications(d, [REC_A1])
            out_dir = os.path.join(d, "IDealwine_normalized", "_delta")
            fname = os.listdir(out_dir)[0]
            with open(os.path.join(out_dir, fname), encoding="utf-8") as fh:
                doc = json.load(fh)
            adj = doc["adjudications"][0]
            self.assertNotIn("wine", adj)
            self.assertNotIn("region", adj)
            self.assertNotIn("product_id", adj)
            self.assertEqual(adj["code"], "2800001")
            self.assertEqual(adj["sold_at"], "2026-08-05T10:00:00+00:00")

    def test_writes_nothing_for_empty_input(self):
        with tempfile.TemporaryDirectory() as d:
            written = _archive_new_adjudications(d, [])
            self.assertEqual(written, 0)


class LoadIdealwineDedupTest(unittest.TestCase):
    def test_same_code_across_two_delta_files_loads_once(self):
        """Confirmed real risk: the manifest's pre-existing checkpoint
        (before this session's full-ISO-precision fix) is a bare date, so
        the first run on the new archive-only path can re-archive an
        adjudication under a second delta file for the same calendar day
        -- load_idealwine must not insert the same adjudication's code
        twice into lots regardless of how many files it appears in."""
        with tempfile.TemporaryDirectory() as d:
            # Two separate archive calls, as two separate runs would
            # produce -- same code reappearing in a second file.
            _archive_new_adjudications(d, [REC_A1])
            _archive_new_adjudications(d, [REC_A1, REC_B])

            conn = sqlite3.connect(":memory:")
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_idealwine(builder, None)
            finally:
                build_db.ARCHIVE = old
            conn.commit()
            rows = conn.execute(
                "SELECT lot_no, hammer_price, realised_price, lot_date "
                "FROM lots ORDER BY lot_no").fetchall()
            conn.close()
            self.assertEqual([r[0] for r in rows],
                             ["2800001", "2800003"])
            # Same field mapping load_idealwine's retired insert_new_lots
            # sibling (direct-DB-insert path) used to cover.
            self.assertAlmostEqual(rows[0][1], 25.0, places=1)
            self.assertAlmostEqual(rows[0][2], 31.46, places=2)
            self.assertEqual(rows[0][3], "2026-08-05")

    def test_genuine_zero_hammer_price_is_not_replaced_by_the_derived_one(
            self):
        """Confirmed real gap: load_idealwine used `a.get("hammer_per_bottle_
        eur") or a.get("hammer_per_bottle_eur_derived")` -- `or` treats an
        observed 0.0 (a genuine donated/no-reserve lot) as falsy and
        silently substitutes the unrelated date-based derived estimate
        instead of keeping the real, observed 0.0 price."""
        rec = dict(REC_A1, code="2800099", hammer_per_bottle_eur=0.0,
                   hammer_per_bottle_eur_derived=99.0)
        with tempfile.TemporaryDirectory() as d:
            _archive_new_adjudications(d, [rec])

            conn = sqlite3.connect(":memory:")
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_idealwine(builder, None)
            finally:
                build_db.ARCHIVE = old
            conn.commit()
            row = conn.execute(
                "SELECT hammer_price FROM lots WHERE lot_no = '2800099'"
                ).fetchone()
            conn.close()
            self.assertEqual(row[0], 0.0)


if __name__ == "__main__":
    unittest.main()
