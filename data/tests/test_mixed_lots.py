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

    def test_plural_mixed_lots_matches(self):
        # Senior-review finding: \b(mixed\s+lot|...)\b failed to match
        # plurals ("mixed lots", "assortments", "selections") because a
        # trailing \b can't match before a plural "s" (no boundary
        # between two word characters) -- the old direct SQL LIKE had no
        # such gate and caught these. matches_keyword() must too.
        kind, reason, _ = m.classify_group([
            lot("Mixed lots of Bordeaux 1975")])
        self.assertEqual(kind, m.KIND_MIXED)
        self.assertEqual(reason, "keyword-evidence")

    def test_plural_assortments_matches(self):
        self.assertTrue(m.matches_keyword("Various assortments of Burgundy"))

    def test_tasting_note_mixed_fruit_not_mixed(self):
        # Senior-review finding: a bare "mixed" keyword (dropped during
        # #93 work after this was confirmed against the real DB) also
        # fires on ordinary tasting-note language for a genuinely single
        # wine ("mixed spices", "mixed fruit", "mixed citrus notes"), not
        # just lot-composition language -- _KEYWORD deliberately stays
        # scoped to "mixed lot"/"mixed case".
        kind, _, _ = m.classify_group([
            lot("Château Margaux 2005",
                description="plenty of mixed spices with hints of prune")])
        self.assertEqual(kind, m.KIND_SINGLE)

    def test_no_wine_name(self):
        kind, _, _ = m.classify_group([lot(None)])
        self.assertEqual(kind, m.KIND_UNKNOWN)


class TestRepeatedVintageSeparator(unittest.TestCase):
    def test_single_marker_not_flagged(self):
        # One "--Vintage" marker is just that one wine's own vintage
        # separator, not evidence of a bundled multi-item lot.
        self.assertFalse(m.has_repeated_vintage_separator(
            "Château Latour--Vintage 1990 (6)"))

    def test_repeated_marker_flagged(self):
        self.assertTrue(m.has_repeated_vintage_separator(
            "Château Palmer--Vintage 1991. C.B. (6) Château L'Angélus"
            "--Vintage 1992. C.B. (6)"))

    def test_french_millesime_variant_flagged(self):
        self.assertTrue(m.has_repeated_vintage_separator(
            "Château Gilette--Millésime/Vintage 1940 (1) Château Gilette,"
            " Doux--Millésime/Vintage 1950 (2)"))

    def test_none_text(self):
        self.assertFalse(m.has_repeated_vintage_separator(None))


if __name__ == "__main__":
    unittest.main()
