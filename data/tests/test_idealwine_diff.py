import unittest

from idealwine_diff import new_adjudications, transform_last_adjudication
from idealwine_normalize import normalize_adjudication

META = {
    "product_id": 882,
    "vintage": 2002,
    "wine": "La Tâche Grand Cru Domaine de la Romanée-Conti",
    "estate": "La Romanée-Conti",
    "region": "BOURGOGNE",
    "appellation": "La Tâche",
    "color": "RED",
    "classification": "GRAND_CRU",
    "bottles": 1,
    "format": "BOUTEILLE",
}

# Current API shape: no more per-sale hammer price, bottle count or wine
# identity -- only id/soldAt/historicPrice per adjudication.
LAST_ADJ = {"id": 2788532, "soldAt": "2026-08-26T14:43:08+00:00",
            "historicPrice": 490620}
OLD_ADJ = {"id": 100, "soldAt": "2026-06-01T00:00:00+00:00",
           "historicPrice": 490620}

COTE = {
    "meta": META,
    "productVintageRatings": [
        {"year": 2025, "value": 428184},
        {"year": 2026, "value": 490620},
    ],
    "lastAdjudications": [LAST_ADJ, OLD_ADJ],
}


class TestTransform(unittest.TestCase):
    def test_maps_prices_to_eur_and_wine_identity(self):
        raw = transform_last_adjudication(LAST_ADJ, META)
        self.assertEqual(raw["sold_at"], "2026-08-26T14:43:08+00:00")
        self.assertEqual(raw["bottles"], 1)
        self.assertIsNone(raw["hammer_eur"])
        self.assertEqual(raw["total_eur"], 4906.2)
        self.assertEqual(raw["code"], "2788532")
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

    def test_normalizes_via_hammer_missing_fallback(self):
        new = new_adjudications([COTE], "2026-07-30T00:00:00+00:00")
        rec = new[0]
        self.assertEqual(rec["total_per_bottle_eur"], 4906.2)
        self.assertEqual(rec["price_basis"], "HAMMER_PLUS_BUYERS_PREMIUM")
        self.assertEqual(rec["buyer_premium_rate"], 0.258)
        self.assertAlmostEqual(rec["hammer_per_bottle_eur_derived"], 3900.0,
                               places=1)


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


if __name__ == "__main__":
    unittest.main()
