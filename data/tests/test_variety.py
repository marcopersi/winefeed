import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wine_resolution.normalize import normalize  # noqa: E402
from wine_resolution import variety as v  # noqa: E402


class TestVariety(unittest.TestCase):
    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), "..", "reference",
                            "varieties.csv")
        self.varieties = v.load_varieties(path)
        self.keys = [normalize(n) for n, _ in self.varieties]

    def test_single_variety(self):
        found = v.match_varieties("Penfolds Bin 707 Cabernet Sauvignon",
                                  self.keys)
        self.assertIn("cabernet sauvignon", found)

    def test_no_variety(self):
        found = v.match_varieties("Château Margaux", self.keys)
        self.assertEqual(found, set())

    def test_blend(self):
        found = v.match_varieties("Cabernet Sauvignon Merlot", self.keys)
        self.assertIn("cabernet sauvignon", found)
        self.assertIn("merlot", found)

    def test_word_boundary(self):
        # "Merlot" must not match inside another word
        found = v.match_varieties("Château Margaux", self.keys)
        self.assertEqual(found, set())


if __name__ == "__main__":
    unittest.main()
