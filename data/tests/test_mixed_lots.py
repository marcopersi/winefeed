import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wine_resolution.normalize import normalize  # noqa: E402
from wine_resolution import mixed_lots as m  # noqa: E402


def lot(wine, wine_key=None, vintage=None, mixed_lot=None, description=None):
    return {
        "wine": wine,
        "wine_key": wine_key if wine_key is not None else normalize(wine),
        "vintage": vintage,
        "mixed_lot": mixed_lot,
        "description": description,
    }


class TestMixedLots(unittest.TestCase):
    def test_provider_flag(self):
        kind, reason, _ = m.classify_group([
            lot("Château Margaux", mixed_lot=1)])
        self.assertEqual(kind, m.KIND_MIXED)
        self.assertEqual(reason, "provider-flag")

    def test_multiple_wines(self):
        kind, reason, _ = m.classify_group([
            lot("Château Margaux"), lot("Château Latour")])
        self.assertEqual(kind, m.KIND_MIXED)
        self.assertEqual(reason, "multiple-wines")

    def test_multiple_vintages_same_wine(self):
        kind, reason, _ = m.classify_group([
            lot("Château Margaux", vintage=2005),
            lot("Château Margaux", vintage=2009)])
        self.assertEqual(kind, m.KIND_MIXED)
        self.assertEqual(reason, "multiple-vintages")

    def test_duplicate_component_not_mixed(self):
        kind, _, _ = m.classify_group([
            lot("Château Margaux", vintage=2005),
            lot("Château Margaux", vintage=2005)])
        self.assertEqual(kind, m.KIND_SINGLE)

    def test_collection_word_not_mixed(self):
        kind, _, _ = m.classify_group([
            lot("Taittinger Collection Artist Series")])
        self.assertEqual(kind, m.KIND_SINGLE)

    def test_keyword_evidence(self):
        kind, reason, _ = m.classify_group([
            lot("Mixed lot Bordeaux")])
        self.assertEqual(kind, m.KIND_MIXED)
        self.assertEqual(reason, "keyword-evidence")

    def test_no_wine_name(self):
        kind, _, _ = m.classify_group([lot(None)])
        self.assertEqual(kind, m.KIND_UNKNOWN)


if __name__ == "__main__":
    unittest.main()
