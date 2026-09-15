import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wine_resolution import spirits as s  # noqa: E402


class TestSpirits(unittest.TestCase):
    def setUp(self):
        path = os.path.join(os.path.dirname(__file__), "..", "reference",
                            "spirits_terms.csv")
        self.terms = s.load_terms(path)

    def test_brand(self):
        self.assertTrue(s.is_spirit("Macallan 25YO", self.terms))

    def test_category(self):
        self.assertTrue(s.is_spirit("Talisker Single Malt Whisky", self.terms))

    def test_wine_not_spirit(self):
        self.assertFalse(s.is_spirit("Château Margaux", self.terms))

    def test_word_boundary(self):
        # "gin" must not match inside "vintage"
        self.assertFalse(s.is_spirit("Château Margaux", self.terms))


if __name__ == "__main__":
    unittest.main()
