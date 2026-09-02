import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wine_resolution import vintage as v  # noqa: E402


class TestVintage(unittest.TestCase):
    def test_leading(self):
        r = v.resolve_vintage("2005 Château Margaux")
        self.assertEqual(r["status"], v.STATUS_EXTRACTED)
        self.assertEqual(r["final"], 2005)

    def test_trailing(self):
        r = v.resolve_vintage("Château Margaux 2005")
        self.assertEqual(r["status"], v.STATUS_EXTRACTED)
        self.assertEqual(r["final"], 2005)
        self.assertEqual(r["cleaned_name"], "Château Margaux")

    def test_vintage_keyword(self):
        r = v.resolve_vintage("Château Margaux--Vintage 2005")
        self.assertEqual(r["status"], v.STATUS_EXTRACTED)
        self.assertEqual(r["final"], 2005)

    def test_nv(self):
        r = v.resolve_vintage("NV Krug")
        self.assertEqual(r["status"], v.STATUS_NV)
        self.assertIsNone(r["final"])

    def test_mv(self):
        r = v.resolve_vintage("MV Krug")
        self.assertEqual(r["status"], v.STATUS_MV)

    def test_vertical_ambiguous(self):
        r = v.resolve_vintage("Vertical 2000/2005/2009")
        self.assertEqual(r["status"], v.STATUS_AMBIGUOUS)

    def test_cuvee_negative(self):
        r = v.resolve_vintage("Cuvee 1949")
        self.assertEqual(r["status"], v.STATUS_MISSING)

    def test_disgorgement_negative(self):
        r = v.resolve_vintage("2013 disgorgement")
        self.assertEqual(r["status"], v.STATUS_MISSING)

    def test_structured_conflict(self):
        r = v.resolve_vintage("Château Margaux 2004", structured_vintage=2005)
        self.assertEqual(r["status"], v.STATUS_CONFLICT)

    def test_year_after_auction(self):
        r = v.resolve_vintage("Château Margaux 2005", auction_year=2004)
        self.assertEqual(r["status"], v.STATUS_INVALID)

    def test_year_before_qty(self):
        r = v.resolve_vintage("Petrus 1968 (6 BT)")
        self.assertEqual(r["status"], v.STATUS_EXTRACTED)
        self.assertEqual(r["final"], 1968)
        self.assertEqual(r["cleaned_name"], "Petrus")

    def test_structured_valid(self):
        r = v.resolve_vintage("Château Margaux 2005", structured_vintage=2005)
        self.assertEqual(r["status"], v.STATUS_STRUCTURED)
        self.assertEqual(r["final"], 2005)


if __name__ == "__main__":
    unittest.main()
