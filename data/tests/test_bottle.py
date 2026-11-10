import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wine_resolution import bottle as b  # noqa: E402


class TestBottleFormat(unittest.TestCase):
    def test_bt(self):
        self.assertEqual(b.parse_bottle_format("La Tâche 2009 (6 BT)"),
                         (6, 7.5))

    def test_mag(self):
        self.assertEqual(b.parse_bottle_format("Morey St. Denis 1996 (6 MAG)"),
                         (6, 15.0))

    def test_dm(self):
        self.assertEqual(b.parse_bottle_format("Château X (2 DM)"), (2, 30.0))

    def test_hb(self):
        self.assertEqual(b.parse_bottle_format("Château X (6 HB)"),
                         (6, 3.75))

    def test_imperiale(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 IMP)"), (1, 60.0))

    def test_methuselah(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 METH)"), (1, 60.0))

    def test_salmanazar(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 SALR)"), (1, 90.0))

    def test_balthazar(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 BALR)"), (1, 120.0))

    def test_nebuchadnezzar(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 NEBR)"), (1, 150.0))

    def test_melchior(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 MELR)"), (1, 180.0))

    def test_liter(self):
        self.assertEqual(b.parse_bottle_format("Petrus 2014 (3 Ltr)"),
                         (1, 30.0))

    def test_no_hint(self):
        self.assertEqual(b.parse_bottle_format("Château Margaux"),
                         (None, None))

    def test_label_state_not_parsed(self):
        # E.T.H / E.L.A are label-state codes, not bottle formats.
        self.assertEqual(
            b.parse_bottle_format("Pomerol (e.t.h dont 1 e.t.a)"),
            (None, None))

    def test_takes_first_recognised(self):
        # "1 BT and Petrus 1985 1 BT" style is rare; ensure a real format wins.
        self.assertEqual(b.parse_bottle_format("Château X (2 BT) (1 MAG)"),
                         (2, 7.5))

class BareWordFallbackTest(unittest.TestCase):
    """Gate-G0 (2026-11-06): hyphenated/spaced compounds ("Double-Magnum")
    and bare, no-leading-count format mentions ("... Magnum"). Split out
    of TestBottleFormat to keep each test class under pylint's
    too-many-public-methods threshold."""

    def test_hyphenated_double_magnum(self):
        # Confirmed real case: besch-cannes' own descriptions write "1
        # Double-Magnum ..." -- the hyphen broke the single-token
        # BOTTLE_FORMATS lookup ("DOUBLEMAGNUM") before this fix, silently
        # falling through to no hint at all.
        self.assertEqual(
            b.parse_bottle_format(None, "1 Double-Magnum CHÂTEAU LARMANDE"),
            (1, 30.0))

    def test_spaced_double_magnum(self):
        self.assertEqual(
            b.parse_bottle_format("Château X 1 Double Magnum"), (1, 30.0))

    def test_bare_magnum_no_leading_count(self):
        # Confirmed real case: dorotheum never puts a count in front
        # ("... 95 Parker-Punkte, Magnum"), so this always fell through
        # to the generic 7.5 dl default -- silently halving
        # price_per_bottle_eur for every such lot. qty is None (not 1):
        # no real count was found, so the caller must not fabricate
        # quantity=1 from this.
        self.assertEqual(
            b.parse_bottle_format(
                "2007 Morillon Zieregg, Weingut Tement, 95 Parker-Punkte,"
                " Magnum"),
            (None, 15.0))

    def test_bare_methuselah_no_leading_count(self):
        self.assertEqual(
            b.parse_bottle_format("Krug Methuselah"), (None, 60.0))

    def test_bare_demi_not_parsed_sec_collision(self):
        # Confirmed real collision -- "Demi-Sec" is a standard Champagne/
        # Vouvray sweetness designation, not a bottle size statement (395
        # live matches). DEMI/HALF are deliberately NOT in the bare-word
        # set for this reason.
        self.assertEqual(
            b.parse_bottle_format(None, "NV Veuve Clicquot Demi-Sec"),
            (None, None))

    def test_bare_half_not_parsed_unrelated_text(self):
        # Confirmed real collision -- "half" turns up in unrelated text
        # far more often than as a size word ("half sweet", "half dozen",
        # even non-wine text).
        self.assertEqual(
            b.parse_bottle_format("MADEIRA RESERVA SOLERA HALF SWEET 1940"),
            (None, None))

    def test_bare_balthazar_not_parsed_producer_collision(self):
        # Confirmed real collision -- Franck Balthazar is a real Cornas
        # producer (158 live matches); "Balthazar" alone must not be read
        # as a 120 dl bottle format.
        self.assertEqual(
            b.parse_bottle_format("2015 Cornas, Les Chaillots, Franck"
                                  " Balthazar"),
            (None, None))

    def test_bare_melchior_not_parsed_brand_collision(self):
        # Confirmed real collision -- "Don Melchior" is Concha y Toro's
        # flagship Chilean wine; "Melchior" alone must not be read as a
        # 180 dl bottle format.
        self.assertEqual(
            b.parse_bottle_format("Don Melchior Cabernet Sauvignon 2000"),
            (None, None))

    def test_bare_dm_not_parsed_productline_collision(self):
        # Confirmed real collision -- "DM" is a real producer's product-
        # line code ("Denton Hill Vineyards DM Chardonnay"), not a bottle
        # format.
        self.assertEqual(
            b.parse_bottle_format("DENTON HILL VINEYARDS DM Chardonnay"),
            (None, None))

    def test_explicit_hint_in_description_wins_over_bare_match_in_name(self):
        # Structural fix: a bare (low-precision) match in `name` must not
        # pre-empt a stronger, explicit-count hint sitting in
        # `description` -- explicit hints are now checked across BOTH
        # texts before the bare fallback is tried on either.
        self.assertEqual(
            b.parse_bottle_format("Krug Methuselah", "(6 BT)"), (6, 7.5))

    def test_bare_jeroboam_still_not_parsed(self):
        # Deliberately NOT in the bare-word set: Jeroboam has no single dl
        # value across regions (3 l Champagne vs. 5 l Bordeaux) -- an
        # explicit leading count/bracket is still required.
        self.assertEqual(
            b.parse_bottle_format(None, "1 Jeroboam CHÂTEAU MOUTON ROTHSCHILD"),
            (None, None))

    def test_bare_imperial_still_not_parsed(self):
        # Deliberately NOT in the bare-word set: collides with the real
        # wine brand CVNE "Imperial" (a Rioja Gran Reserva), confirmed
        # live among winefields' lots -- "Imperial" alone must not be
        # read as a 60 dl bottle format.
        self.assertEqual(
            b.parse_bottle_format("Rioja 'Imperial' Gran Reserva 1988"),
            (None, None))


class TestStripBottleFormat(unittest.TestCase):
    """Confirmed real case: "Sassicaia" vs. "Sassicaia (2 BT)" vs.
    "Sassicaia (3 BT)" fragment into separate wines rows for the same
    real wine because the bottle-format hint was never removed from the
    name used to build alias_key."""

    def test_strips_trailing_bracket(self):
        self.assertEqual(b.strip_bottle_format("Sassicaia (2 BT)"),
                          "Sassicaia")

    def test_strips_mid_name_bracket(self):
        self.assertEqual(
            b.strip_bottle_format("Sassicaia (6 BT) 1990"), "Sassicaia 1990")

    def test_strips_plain_form(self):
        self.assertEqual(b.strip_bottle_format("Krug 1 Magnum"), "Krug")

    def test_strips_hyphenated_double_magnum(self):
        # Gate-G0 review fix: confirmed real fragmentation -- parse_
        # bottle_format already sizes this correctly (30.0 dl via its
        # own _COMPOUND normalization), but strip_bottle_format left the
        # hyphenated text in the name, so "1 Double-Magnum CHÂTEAU
        # LARMANDE" and "CHÂTEAU LARMANDE" resolved to two different
        # wine_ref_id rows for the same real wine.
        self.assertEqual(
            b.strip_bottle_format("1 Double-Magnum CHÂTEAU LARMANDE"),
            "CHÂTEAU LARMANDE")

    def test_strips_spaced_double_magnum(self):
        self.assertEqual(
            b.strip_bottle_format("Château X 1 Double Magnum"),
            "Château X")

    def test_strips_liter_form(self):
        self.assertEqual(b.strip_bottle_format("Petrus 2014 3 Ltr"),
                          "Petrus 2014")

    def test_no_match_is_unchanged(self):
        self.assertEqual(b.strip_bottle_format("Château Margaux"),
                          "Château Margaux")

    def test_label_state_code_not_stripped(self):
        self.assertEqual(
            b.strip_bottle_format("Pomerol (e.t.h dont 1 e.t.a)"),
            "Pomerol (e.t.h dont 1 e.t.a)")

    def test_empty_is_unchanged(self):
        self.assertEqual(b.strip_bottle_format(""), "")
        self.assertIsNone(b.strip_bottle_format(None))


if __name__ == "__main__":
    unittest.main()
