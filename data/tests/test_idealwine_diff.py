import os
import sqlite3
import tempfile
import unittest

from idealwine_diff import (insert_new_lots, new_adjudications,
                            transform_last_adjudication)
from idealwine_normalize import normalize_adjudication

LAST_ADJ = {
    "code": "2788532",
    "soldAt": "2026-08-26T14:43:08+00:00",
    "price": 390000,
    "historicPrice": 490620,
    "numberOfBottles": 1,
    "format": "BOUTEILLE",
    "productVintage": {
        "year": 2002,
        "product": {
            "id": 882,
            "name": "La Tâche Grand Cru Domaine de la Romanée-Conti",
            "estate": {"name": "La Romanée-Conti"},
            "region": {"name": "BOURGOGNE"},
            "appellation": "La Tâche",
            "color": "RED",
            "classification": "GRAND_CRU",
        },
    },
}

OLD_ADJ = dict(LAST_ADJ, soldAt="2026-06-01T00:00:00+00:00", code="100")

COTE = {
    "currentYearRating": 490620,
    "productVintageRatings": [
        {"year": 2025, "value": 428184},
        {"year": 2026, "value": 490620},
    ],
    "productVintage": {"product": {"id": 882}},
    "lastAdjudications": [LAST_ADJ, OLD_ADJ],
}


class TestTransform(unittest.TestCase):
    def test_maps_prices_to_eur_and_wine_identity(self):
        raw = transform_last_adjudication(LAST_ADJ)
        self.assertEqual(raw["sold_at"], "2026-08-26T14:43:08+00:00")
        self.assertEqual(raw["bottles"], 1)
        self.assertEqual(raw["hammer_eur"], 3900.0)
        self.assertEqual(raw["total_eur"], 4906.2)
        self.assertEqual(raw["vintage"], 2002)
        self.assertEqual(raw["wine"], "La Tâche Grand Cru Domaine de la "
                                       "Romanée-Conti")
        self.assertEqual(raw["estate"], "La Romanée-Conti")
        self.assertEqual(raw["region"], "BOURGOGNE")


class TestDiff(unittest.TestCase):
    def test_only_newer_adjudications_survive(self):
        new = new_adjudications([COTE], "2026-07-30T00:00:00+00:00")
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["code"], "2788532")

    def test_normalizes_hammer_and_premium(self):
        new = new_adjudications([COTE], "2026-07-30T00:00:00+00:00")
        rec = new[0]
        self.assertEqual(rec["hammer_per_bottle_eur"], 3900.0)
        self.assertEqual(rec["total_per_bottle_eur"], 4906.2)
        self.assertEqual(rec["price_basis"], "HAMMER")
        self.assertEqual(rec["buyer_premium_rate"], 0.258)


class TestNormalize(unittest.TestCase):
    def test_missing_hammer_derives_from_premium_rate(self):
        raw = {"sold_at": "2026-08-26T00:00:00+00:00", "bottles": 1,
               "hammer_eur": None, "total_eur": 4906.2, "format": "BOUTEILLE",
               "code": "x"}
        rec, code = normalize_adjudication(raw, False, None, {})
        self.assertEqual(code, "price_null")
        self.assertAlmostEqual(rec["hammer_per_bottle_eur_derived"], 3900.0,
                               places=1)
        self.assertEqual(rec["price_basis"], "HAMMER_PLUS_BUYERS_PREMIUM")

    def test_duclot_marked_mixed_case(self):
        raw = {"sold_at": "2026-08-26T00:00:00+00:00", "bottles": 1,
               "hammer_eur": 100.0, "total_eur": 126.0, "format": "BOUTEILLE",
               "code": "x"}
        rec, code = normalize_adjudication(raw, True, None, {})
        self.assertEqual(code, "mixed_case")
        self.assertEqual(rec["anomaly_type"], "MIXED_CASE")


class TestInsert(unittest.TestCase):
    def test_insert_and_dedup(self):
        from build_db import SCHEMA

        tmp = tempfile.mktemp(suffix=".sqlite")
        try:
            conn = sqlite3.connect(tmp)
            conn.executescript(SCHEMA)
            new = new_adjudications([COTE], "2026-07-30T00:00:00+00:00")
            self.assertEqual(insert_new_lots(conn, new), 1)
            self.assertEqual(insert_new_lots(conn, new), 0)
            row = conn.execute(
                "SELECT hammer_price, realised_price, lot_date "
                "FROM lots").fetchone()
            self.assertEqual(row, (3900.0, 4906.2, "2026-08-26"))
            conn.close()
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)


if __name__ == "__main__":
    unittest.main()
