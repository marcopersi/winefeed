"""parse_christies_secondary: Christie's own structured ``secondary`` field
(e.g. "12 Bottles (75cl) per lot") -> (quantity, bottle_size_dl) or a MIXED
sentinel.

Each case here is a real example pulled from the archive (not invented),
surfaced while investigating the Stufe-1 QTY_ASSUMED finding
(docs/price-prediction-plan.md).
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


def _parse(secondary, title=None):
    # Existing assertions below predate the ``size_assumed`` 3rd element
    # (finding 4, senior review, G0.7b round) -- slice it off here so
    # they stay unchanged; ``_parse_full`` is for the dedicated flag
    # tests that need the 3rd element.
    r = build_db.parse_christies_secondary(secondary, title)
    return r[:2] if isinstance(r, tuple) else r


def _parse_full(secondary, title=None):
    return build_db.parse_christies_secondary(secondary, title)


class ChristiesSecondaryParseTest(unittest.TestCase):
    def test_plain_bottles_per_lot(self):
        self.assertEqual(_parse("6 bottles per lot"), (6, 7.5))

    def test_singular_bottle(self):
        self.assertEqual(_parse("1 bottle per lot"), (1, 7.5))

    def test_dozen_bottles_per_lot(self):
        self.assertEqual(_parse("1 dozen bottles per lot"), (12, 7.5))

    def test_dozen_bottles_per_dozen(self):
        # Real example (lot 155, Château Belair 1982): "per dozen" is a
        # second, redundant denominator wording, not a different quantity.
        self.assertEqual(_parse("3 dozen bottles per dozen"), (36, 7.5))

    def test_word_number_dozen(self):
        self.assertEqual(_parse("two dozen bottles per lot"), (24, 7.5))

    def test_dozen_and_extra_bottles(self):
        self.assertEqual(
            _parse("1 dozen and 6 bottles per dozen"), (18, 7.5))

    def test_explicit_size_in_parens(self):
        self.assertEqual(
            _parse("3 Bottles (75cl) per lot"), (3, 7.5))

    def test_explicit_size_with_packaging_suffix(self):
        self.assertEqual(
            _parse("12 Bottles (75cl) per lot - (2owc)"), (12, 7.5))

    def test_explicit_size_no_parens(self):
        self.assertEqual(_parse("2 65cl bottles per lot"), (2, 6.5))

    def test_magnum(self):
        self.assertEqual(_parse("6 magnums per lot"), (6, 15.0))

    def test_magnum_with_explicit_cl(self):
        self.assertEqual(
            _parse("4 Magnums (150cl) per lot"), (4, 15.0))

    def test_double_magnum(self):
        self.assertEqual(_parse("1 double-magnum per lot"), (1, 30.0))

    def test_imperiale(self):
        # Real example, lot 591, Château Latour 1961.
        self.assertEqual(_parse("1 impériale per lot"), (1, 60.0))

    def test_french_bilingual_bottle(self):
        self.assertEqual(_parse("3 bouteilles/bottles par lot"), (3, 7.5))

    def test_french_bilingual_singular(self):
        self.assertEqual(_parse("1 bouteille/bottle par lot"), (1, 7.5))

    def test_above_n_is_treated_as_point_estimate(self):
        # Confirmed decision: a lower bound Christie's itself prints is
        # used as the value (understates qty, so OVERstates
        # price_per_bottle_eur if the true count is higher -- never
        # silently understates the price).
        self.assertEqual(_parse("Above 3 bottles per lot"), (3, 7.5))

    def test_above_n_bilingual_slash_form(self):
        self.assertEqual(
            _parse("6 bouteilles/Above 6 bottles par lot"), (6, 7.5))

    def test_above_n_bilingual_slash_mismatch_uses_smaller(self):
        # Real archive example: the French exact count and the English
        # "Above N" floor disagree -- the smaller is the conservative
        # choice (same principle as "Above N" alone), not whichever
        # number happens to appear first.
        self.assertEqual(
            _parse("13 bouteilles/Above 14 bottles par lot"), (13, 7.5))
        self.assertEqual(
            _parse("29 bouteilles/Above 28 bottles par lot"), (28, 7.5))

    def test_jeroboam_bordeaux_default(self):
        self.assertEqual(
            _parse("1 jeroboam per lot", "Château Latour--Vintage 1990"),
            (1, 50.0))

    def test_jeroboam_accented_french_spelling(self):
        # Senior-review finding: the accented spelling is captured by
        # the surrounding regex (its unit-word character class already
        # allows "é") but _christies_format_dl's own jeroboam check was
        # ASCII-only, silently reverting to QTY_ASSUMED instead of
        # disambiguating -- same bilingual-template pattern this
        # function already handles for "impériale"/"imperial".
        self.assertEqual(
            _parse("1 jéroboam per lot", "Château Latour--Vintage 1990"),
            (1, 50.0))
        self.assertEqual(
            _parse("1 jéroboam per lot", "Veuve Clicquot 1975"), (1, 30.0))

    def test_jeroboam_champagne_by_producer_name(self):
        # "Champagne" never appears in the title text itself for most
        # real examples -- the producer name is the only signal.
        self.assertEqual(
            _parse("1 jeroboam per lot", "Veuve Clicquot 1975"),
            (1, 30.0))

    def test_jeroboam_champagne_by_explicit_word(self):
        self.assertEqual(
            _parse("1 jeroboam per lot", "Champagne Krug 1988"),
            (1, 30.0))

    def test_barrel_is_mixed_sentinel(self):
        self.assertEqual(_parse("1 Barrel per lot"), "MIXED")

    def test_piece_is_mixed_sentinel(self):
        self.assertEqual(_parse("1 pièce par lot"), "MIXED")

    def test_cigars_is_mixed_sentinel(self):
        self.assertEqual(_parse("1 box of 50 cigars per lot"), "MIXED")

    def test_genuine_mixed_format_is_mixed_sentinel(self):
        self.assertEqual(
            _parse("1 magnum and 34 bottles per lot"), "MIXED")

    def test_dozen_and_bottles_is_not_mixed_format(self):
        # Same format (bottles) on both sides of the compound phrase --
        # must NOT be classified MIXED just because the words differ
        # ("dozen" vs "bottles").
        self.assertEqual(
            _parse("1 dozen and 6 bottles per dozen"), (18, 7.5))

    def test_same_format_spelling_variants_are_not_mixed(self):
        # Code-review finding: comparing the literal unit spelling
        # ("impériale" vs "imperial") instead of the RESOLVED dl wrongly
        # classified this one real 60.0dl format, spelled two ways, as a
        # genuine mixed-format lot.
        self.assertEqual(
            _parse("1 impériale and 1 imperial per lot"), (2, 60.0))

    def test_champagne_house_match_is_word_bounded(self):
        # Code-review finding: an unbounded substring match resolved
        # "Mumm" inside an unrelated word ("Mummius"), mis-sizing a
        # Bordeaux jeroboam to the Champagne 3l convention.
        self.assertEqual(
            _parse("1 jeroboam per lot", "Chateau Mummius 1990"), (1, 50.0))

    def test_garbled_ditto_artifact_returns_none(self):
        self.assertIsNone(_parse("1 ^,,^^,,^"))

    def test_denominator_repeats_unit_instead_of_lot(self):
        # Real archive form: the denominator restates the numerator
        # ("6 magnums per 6 magnums") instead of saying "per lot".
        self.assertEqual(_parse("6 magnums per 6 magnums"), (6, 15.0))
        self.assertEqual(
            _parse("1 jeroboam per jeroboam", "Château Latour 1990"),
            (1, 50.0))
        self.assertEqual(
            _parse("1 impériale per imperiale"), (1, 60.0))

    def test_missing_per_lot_tail(self):
        # Real archive form: no "per lot"/"per dozen" at all.
        self.assertEqual(_parse("1 dozen bottles"), (12, 7.5))
        self.assertEqual(_parse("6 magnums"), (6, 15.0))

    def test_impriale_typo_alias(self):
        self.assertEqual(_parse("1 impriale per lot"), (1, 60.0))

    def test_imperial_masculine_french_spelling(self):
        self.assertEqual(_parse("1 impérial per lot"), (1, 60.0))

    def test_space_separated_double_magnum(self):
        self.assertEqual(_parse("2 double magnums per lot"), (2, 30.0))

    def test_space_separated_half_bottle(self):
        self.assertEqual(_parse("24 half bottles per lot"), (24, 3.75))

    def test_half_litre_bottle_wording(self):
        self.assertEqual(_parse("1 half-litre bottle per lot"), (1, 5.0))

    def test_ml_explicit_size(self):
        self.assertEqual(_parse("1 bottle (700ml) per lot"), (1, 7.0))

    def test_x_separator_between_count_and_size(self):
        self.assertEqual(_parse("1 x 70cl bottle per lot"), (1, 7.0))

    def test_doubled_leading_count_typo(self):
        self.assertEqual(_parse("24 24 bottles per lot"), (24, 7.5))

    def test_bottles_only_qualifier(self):
        # "only" marks a partial dozen -- the number itself is already
        # the real count, not multiplied by 12.
        self.assertEqual(_parse("11 bottles only per dozen"), (11, 7.5))

    def test_bilingual_english_per_lot_not_just_french_par_lot(self):
        self.assertEqual(
            _parse("12 bouteilles/bottles per lot"), (12, 7.5))

    def test_region_name_only_returns_none(self):
        # Real archive form: ``secondary`` occasionally holds a region
        # name instead of any quantity/format information at all.
        self.assertIsNone(_parse("Napa Valley"))
        self.assertIsNone(_parse("Rhône"))

    def test_empty_returns_none(self):
        self.assertIsNone(_parse(""))
        self.assertIsNone(_parse(None))

    def test_exotic_unrecognised_format_returns_none(self):
        # Real archive example: not force-parsed, left for the caller's
        # existing QTY_ASSUMED default.
        self.assertIsNone(_parse("2 x 1 gallon flasks per lot"))

    def test_typo_par_lat_returns_none(self):
        self.assertIsNone(_parse("12 bouteilles/bottles par lat"))

    def test_bare_jeroboam_is_size_assumed(self):
        # Finding 4 (senior review, G0.7b round): no explicit size given,
        # so the Bordeaux-vs-Champagne convention is a guess either way
        # -- flagged size_assumed, not a confirmed size.
        self.assertEqual(
            _parse_full("1 jeroboam per lot", "Château Latour 1990"),
            (1, 50.0, True))
        self.assertEqual(
            _parse_full("1 jeroboam per lot", "Veuve Clicquot 1975"),
            (1, 30.0, True))

    def test_explicit_size_jeroboam_is_not_size_assumed(self):
        self.assertEqual(
            _parse_full("1 Jeroboam (500cl) per lot"), (1, 50.0, False))

    def test_non_jeroboam_named_format_is_not_size_assumed(self):
        self.assertEqual(_parse_full("6 magnums per lot"), (6, 15.0, False))
        self.assertEqual(
            _parse_full("1 impériale per lot"), (1, 60.0, False))

    def test_mixed_format_jeroboam_side_is_size_assumed(self):
        self.assertEqual(
            _parse_full("1 jeroboam and 1 jeroboam per lot",
                         "Château Latour 1990"),
            (2, 50.0, True))


if __name__ == "__main__":
    unittest.main()
