"""_weinauktion_parse_qty_size: the weinauktion-platform (steinfels /
weinboerse) lot ``description`` field -> (quantity, bottle_size_dl) or a
MIXED sentinel.

Each case here is a real example pulled from the steinfels archive (not
invented), surfaced after the user pointed out that steinfels always
states quantity and price per lot -- a gap this function closes
(docs/price-prediction-plan.md Stufe-1 QTY_ASSUMED investigation, D21).
"""
# pylint: disable=protected-access,too-many-public-methods
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


def _parse(desc):
    # Existing assertions below predate the ``size_assumed`` 3rd element
    # (finding 4, senior review, G0.7b round) -- slice it off here so
    # they stay unchanged; ``_parse_full`` is for the dedicated flag
    # tests that need the 3rd element.
    r = build_db._weinauktion_parse_qty_size(desc)
    return r[:2] if isinstance(r, tuple) else r


def _parse_full(desc):
    return build_db._weinauktion_parse_qty_size(desc)


class WeinauktionQtySizeParseTest(unittest.TestCase):
    def test_full_description_with_wine_name_lines(self):
        # Real example (Steinfels/2016/eAuktion6/Resultfile2.json, item 649).
        self.assertEqual(
            _parse(
                "<div >Schätzpreis: <span >80 CHF</span></div>"
                "<strong>VENETO Villa Erbice,</strong><BR>"
                "Recioto della Valpolicella Torrazzine 2002<BR>"
                "4 50cl-Flaschen<BR>"),
            (4, 5.0))

    def test_size_before_unit_word(self):
        self.assertEqual(_parse("4 50cl-Flaschen"), (4, 5.0))
        self.assertEqual(_parse("6 35cl Flaschen"), (6, 3.5))

    def test_size_after_unit_word(self):
        self.assertEqual(_parse("1 Flasche 70cl"), (1, 7.0))
        self.assertEqual(_parse("6 Flaschen 50cl"), (6, 5.0))

    def test_trailing_packaging_note_is_ignored(self):
        # Real archive forms: a redundant "<N>er OC/OHK" packaging note
        # after the real quantity, not a second quantity.
        self.assertEqual(_parse("12 Flaschen 6er OC"), (12, 7.5))
        self.assertEqual(_parse("5 Flaschen in 6er OC"), (5, 7.5))

    def test_fraction_size_modifier(self):
        # "5 3/8 Flaschen" = 5 bottles of 3/8 litre (0.375l half-bottles).
        self.assertEqual(_parse("5 3/8 Flaschen"), (5, 3.75))

    def test_explicit_cl_size_on_named_large_format(self):
        self.assertEqual(_parse("1 Jéroboam 300cl OHK"), (1, 30.0))
        self.assertEqual(_parse("1 Jéroboam 500cl OHK"), (1, 50.0))

    def test_explicit_liter_size_variants_on_named_large_format(self):
        self.assertEqual(_parse("1 Jéroboam 3-Liter OHK"), (1, 30.0))
        self.assertEqual(_parse("1 Jéroboam 5L OHK"), (1, 50.0))
        self.assertEqual(_parse("1 Jéroboam 5-Litre OHK"), (1, 50.0))
        self.assertEqual(_parse("1 Jéroboam 4.5L OHK"), (1, 45.0))

    def test_bare_named_format_has_no_bordeaux_champagne_ambiguity_here(self):
        # Unlike christies' ``secondary`` field: when no explicit size is
        # given at all (confirmed real residual, <5% of jeroboam-format
        # lots), the Bordeaux convention (5l) is the fallback, same
        # constant value as christies' own default for that residual.
        self.assertEqual(_parse("1 Jéroboam"), (1, 50.0))

    def test_bare_liter_unit_means_one_litre(self):
        self.assertEqual(_parse("1 Liter Flasche"), (1, 10.0))
        self.assertEqual(_parse("1 Liter-Flasche"), (1, 10.0))

    def test_explicit_size_overrides_named_default(self):
        self.assertEqual(_parse("6 Liter-Flaschen"), (6, 10.0))
        self.assertEqual(_parse("1 Balthasar 12-Liter OHK"), (1, 120.0))

    def test_methusalem_spelling_variants(self):
        # Real archive spellings, all the same 60.0dl format as
        # "methuselah".
        self.assertEqual(_parse("1 Methusalem 6-Liter"), (1, 60.0))
        self.assertEqual(_parse("1 Mathusalem 6-Liter OHK"), (1, 60.0))

    def test_space_separated_double_magnum(self):
        self.assertEqual(_parse("1 double magnum"), (1, 30.0))

    def test_space_separated_half_bottles(self):
        self.assertEqual(_parse("2 half bottles"), (2, 3.75))

    def test_decanter_is_mixed_sentinel(self):
        # Real archive examples: a decorative decanter, not a plain wine
        # bottle -- price-per-bottle has no clean meaning for it.
        self.assertEqual(
            _parse("1 Muranoglas Dekanter 70cl OHK"), "MIXED")
        self.assertEqual(_parse("1 Ceramic Decanter blue OC"), "MIXED")

    def test_generic_piece_count_returns_none(self):
        # Real archive form: "Stück" alone carries no format/size
        # information at all -- left for the caller's QTY_ASSUMED
        # default, not guessed.
        self.assertIsNone(_parse("1 Stück"))
        self.assertIsNone(_parse("6 Stück OC"))

    def test_multi_item_container_returns_none(self):
        self.assertIsNone(_parse("1 Set"))
        self.assertIsNone(_parse("1 Sammlerkiste"))

    def test_unrelated_number_elsewhere_in_segment_is_not_the_size(self):
        # Code-review finding: the explicit-size lookup must be anchored
        # right after the unit word, not a bare search over the rest of
        # the segment -- otherwise an unrelated number elsewhere (a
        # damage note, a different item) gets picked up as the bottle
        # size.
        self.assertEqual(
            _parse("6 Flaschen in Holzkiste, Transportschaden 2cl Verlust"),
            (6, 7.5))
        self.assertEqual(
            _parse("6 Flaschen Lafite 2015, dazu 1 Liter Olivenoel"),
            (6, 7.5))

    def test_plural_decanter_is_mixed_sentinel(self):
        # Code-review finding: the trailing \b failed to match a directly
        # attached plural suffix ("Karaffen", "Decanters").
        self.assertEqual(_parse("2 Karaffen 70cl OHK"), "MIXED")
        self.assertEqual(_parse("2 Decanters 70cl OHK"), "MIXED")

    def test_empty_returns_none(self):
        self.assertIsNone(_parse(""))
        self.assertIsNone(_parse(None))

    def test_bare_named_format_jeroboam_is_size_assumed(self):
        # Finding 4 (senior review, G0.7b round): no explicit cl/Liter
        # size given, so the Bordeaux-convention default is a guess --
        # flagged size_assumed, not a confirmed size.
        self.assertEqual(_parse_full("1 Jéroboam"), (1, 50.0, True))

    def test_bare_jeroboam_uses_champagne_house_heuristic_from_wine_text(
            self):
        # Senior-review finding: this used to default straight to
        # Bordeaux with no producer check at all, even though the same
        # Champagne-house signal christies' own jeroboam disambiguation
        # uses is available in these lots' own wine text -- giving the
        # identical ambiguity worse accuracy here than at christies for
        # no real reason.
        self.assertEqual(
            build_db._weinauktion_parse_qty_size(
                "1 Jéroboam", "Château Latour 1990"),
            (1, 50.0, True))
        self.assertEqual(
            build_db._weinauktion_parse_qty_size(
                "1 Jéroboam", "Veuve Clicquot 1975"),
            (1, 30.0, True))
        # An explicit size still overrides regardless of producer, and
        # is never flagged as a guess -- unaffected by this heuristic.
        self.assertEqual(
            build_db._weinauktion_parse_qty_size(
                "1 Jéroboam 300cl OHK", "Veuve Clicquot 1975"),
            (1, 30.0, False))

    def test_explicit_size_jeroboam_is_not_size_assumed(self):
        self.assertEqual(
            _parse_full("1 Jéroboam 500cl OHK"), (1, 50.0, False))
        self.assertEqual(
            _parse_full("1 Jéroboam 5L OHK"), (1, 50.0, False))

    def test_non_jeroboam_bare_named_format_is_not_size_assumed(self):
        # Every other bare-name fallback resolves to one single,
        # unambiguous fixed size -- not a guess.
        self.assertEqual(
            _parse_full("1 double magnum"), (1, 30.0, False))
        self.assertEqual(
            _parse_full("1 Methusalem 6-Liter"), (1, 60.0, False))

    def test_explicit_size_overrides_named_default_is_not_size_assumed(self):
        self.assertEqual(
            _parse_full("1 Liter Flasche"), (1, 10.0, False))


if __name__ == "__main__":
    unittest.main()
