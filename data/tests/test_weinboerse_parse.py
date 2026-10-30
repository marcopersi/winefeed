"""_wb_parse_description: Weinbörse's free-text lot description -> fields.

Each case here is a real example pulled from the archive (not invented),
chosen because it broke an earlier version of the parser.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


def _parse(desc):
    errors = []
    result = build_db._wb_parse_description(desc, ("t", 0), errors)
    return result, errors


class WeinboerseParseTest(unittest.TestCase):
    def test_slash_style_basic(self):
        r, errors = _parse(
            "Burgund rot / AMIOT-SERVELLE<br />"
            "Chambolle-Musigny 1er Les Charmes<br />"
            "Jahrgang: 2004<br /><b>3 Flaschen</b><br /><br />"
            "<b>Schätzpreis: 120 - 210 CHF</b>")
        self.assertEqual(errors, [])
        self.assertEqual(r["producer"], "AMIOT-SERVELLE")
        self.assertEqual(r["wine"], "Chambolle-Musigny 1er Les Charmes")
        self.assertEqual(r["vintage"], 2004)
        self.assertEqual((r["quantity"], r["bottle_size_dl"]), (3, 7.5))
        self.assertFalse(r["is_ohk"])
        self.assertFalse(r["mixed_lot"])
        self.assertEqual((r["region"], r["color"]), ("Burgund", "Rot"))

    def test_producer_after_last_slash_not_first(self):
        """'USA / Kalifornien / HEITZ' -- producer is after the LAST slash,
        region is everything before it."""
        r, _ = _parse(
            "USA / Kalifornien / HEITZ<br />CS Napa Martha's Vineyard<br />"
            "Jahrgang: 2015<br /><b>6 Flaschen</b><br /><br />")
        self.assertEqual(r["producer"], "HEITZ")
        self.assertEqual(r["region"], "USA / Kalifornien")

    def test_ohk_does_not_false_positive_on_embedded_oc_substring(self):
        """'Ockfener Bockstein' and a producer-fallback wine ending in
        '...MEDOC' must not be truncated -- OC/OHK need real boundaries."""
        r, _ = _parse(
            "Deutschland / VON HOVEL<br />Riesling Ockfener Bockstein<br />"
            "Jahrgang: 2018<br /><b>6 Flaschen</b><br /><br />")
        self.assertFalse(r["is_ohk"])
        self.assertEqual(r["wine"], "Riesling Ockfener Bockstein")

        r2, _ = _parse(
            "Bordeaux rot / CHATEAU LA MISSION HAUT-BRION MEDOC<br />OHK"
            "<br />Jahrgang: 1979<br /><b>1 Flasche</b><br /><br />")
        self.assertEqual(r2["wine"], "CHATEAU LA MISSION HAUT-BRION MEDOC")
        self.assertTrue(r2["is_ohk"])

    def test_ohk_is_case_sensitive_pays_doc_is_not_ohk(self):
        """Lowercase 'Oc' in "Pays d'Oc" (Languedoc) must not match --
        the source always writes the real markers uppercase."""
        r, _ = _parse(
            "Languedoc / DOMAINE X<br />Pays d'Oc Rouge<br />"
            "Jahrgang: 2018<br /><b>6 Flaschen</b><br /><br />")
        self.assertFalse(r["is_ohk"])
        self.assertEqual(r["wine"], "Pays d'Oc Rouge")

    def test_ohk_suffix_on_wine_name(self):
        r, _ = _parse(
            "Burgund rot / DOMAINE DUJAC<br />Clos de la Roche gr.c., OHK"
            "<br />Jahrgang: 2011<br /><b>3 Flaschen</b><br /><br />")
        self.assertTrue(r["is_ohk"])
        self.assertEqual(r["wine"], "Clos de la Roche gr.c.")

    def test_ohk_prefix_before_condition_note(self):
        """'OHK ohne Deckel, ...' -- OHK as a line of its own, not a
        trailing suffix on the wine name."""
        r, _ = _parse(
            "Bordeaux rot / CHATEAU MARGAUX<br />OHK ohne Deckel, Etikett "
            "leicht defekt und verfärbt<br />Jahrgang: 1985<br />"
            "<b>1 Magnum 1.5L</b><br /><br />")
        self.assertTrue(r["is_ohk"])
        self.assertEqual((r["quantity"], r["bottle_size_dl"]), (1, 15.0))

    def test_chateau_only_lot_falls_back_to_producer_as_wine(self):
        """First-growth-style lots with no separate wine-name line at all."""
        r, errors = _parse(
            "Bordeaux rot / CHATEAU ANGELUS<br /><br />Jahrgang: 1995<br />"
            "<b>2 Flaschen</b><br /><br />")
        self.assertEqual(errors, [])
        self.assertEqual(r["wine"], "CHATEAU ANGELUS")
        self.assertEqual(r["producer"], "CHATEAU ANGELUS")

    def test_eighth_bottle_fraction_is_a_size_not_a_quantity_modifier(self):
        """'12 3/8 Flaschen' = 12 x 0.375L bottles, not 12 and 3/8 of one."""
        r, _ = _parse(
            "Bordeaux rot / CHATEAU CALON-SEGUR<br /><br />Jahrgang: 2005"
            "<br /><b>12 3/8 Flaschen</b><br /><br />")
        self.assertEqual((r["quantity"], r["bottle_size_dl"]), (12, 3.75))

    def test_explicit_liters_override_named_format_default(self):
        """A Bordeaux Jeroboam is 5L, not the Champagne 3L -- when the
        source states the liters explicitly, trust that over the name."""
        r, _ = _parse(
            "Bordeaux rot / CHATEAU LA MISSION HAUT-BRION<br />5L, 3.7cm, "
            "OHK ohne Deckel<br />Jahrgang: 1979<br /><b>1 Jeroboam 5L</b>"
            "<br /><br />")
        self.assertEqual(r["bottle_size_dl"], 50.0)

    def test_named_large_format_without_explicit_liters(self):
        r, _ = _parse(
            "Bordeaux rot / CHATEAU BRANDA<br />OHK<br />Jahrgang: 1998"
            "<br /><b>1 BAL</b><br /><br />")
        self.assertEqual(r["bottle_size_dl"], 120.0)

    def test_ohk_prefix_with_leading_connector_word(self):
        """'...<br>in 6er OHK<br>...' -- the OHK note is its own line
        glued with a leading 'in'; stripping it must not leave a dangling
        'in' behind on the wine name."""
        r, _ = _parse(
            "<b>WEINGUT BERNHARD HUBER (Baden)</b><br>"
            "Spätburgunder GG Wildenstein 'R'<br>2012<br>"
            "<b>3 Flaschen</b><br><br>in 6er OHK<br><b>RP93+</b>")
        self.assertEqual(r["wine"], "Spätburgunder GG Wildenstein 'R'")
        self.assertTrue(r["is_ohk"])

    def test_mixed_subwine_with_leading_size_token_is_still_real(self):
        """'1x 0.75L Pinot Noir Monolith, ...' -- the explicit bottle size
        prefix must not hide that this sub-item is a real second wine."""
        r, _ = _parse(
            "<b>AUSWAHL GRAUBÜNDEN</b><br>1x 0.75L Pinot Noir Monolith, "
            "Obrecht, 1x 1.5L Pinot Noir, Studach, 1.5cm<br>2015<br>"
            "<b>2 Flaschen</b><br><br><b></b>")
        self.assertIsNone(r["producer"])  # German "Choix de" placeholder
        self.assertTrue(r["mixed_lot"])

    def test_div_unit_for_mixed_assortment_has_no_single_size(self):
        r, _ = _parse(
            "Mixed Lots / MIXED LOT<br />3x 0.375L Grande Cuvée BA 1991, "
            "Kracher,<br />2x 0.75L Grand Merlot 1991, James Irvine<br />"
            "<br /><b>6 Div.</b><br /><br />")
        self.assertIsNone(r["bottle_size_dl"])
        self.assertEqual(r["quantity"], 6)
        self.assertIsNone(r["producer"])  # placeholder, not a real producer
        self.assertTrue(r["mixed_lot"])

    def test_choix_de_bordeaux_placeholder_producer_and_real_mix(self):
        r, _ = _parse(
            "Bordeaux rot / CHOIX DE BORDEAUX<br />6x Conseillante 1994, "
            "3x Gazin 1995<br /><br /><b>9 Flaschen</b><br /><br />")
        self.assertIsNone(r["producer"])
        self.assertTrue(r["mixed_lot"])

    def test_condition_note_counts_are_not_mistaken_for_a_second_wine(self):
        """'4x befleckt, 1x defekt' describes bottle condition, not two
        more wines in the lot."""
        r, _ = _parse(
            "Burgund rot / DOMAINE DUJAC<br />Morey-St.-Denis 1er cru, "
            "Etiketten: 4x befleckt, 1x defekt<br />Jahrgang: 1982<br />"
            "<b>4 Flaschen</b><br /><br />")
        self.assertFalse(r["mixed_lot"])

    def test_condition_codes_with_year_groups_are_not_mistaken_for_a_mix(self):
        """A single wine sold across vintages/condition grades, e.g.
        '1x 1985 (RP96), Etikett ..., 2x 1988 (WS95), 1x HS/TS' -- none of
        those groups is a second real wine."""
        r, _ = _parse(
            "<b>CHATEAU LEOVILLE LAS CASES</b><br>1x 1985 (RP96, WS98), "
            "Etikett ganz leicht befleckt,<br>2x 1988 (WS95), 1x HS/TS"
            "<br><b>3 Flaschen</b><br><br><b></b>")
        self.assertFalse(r["mixed_lot"])
        self.assertEqual(r["producer"], "CHATEAU LEOVILLE LAS CASES")

    def test_mixed_vintage_single_wine_is_not_mixed_lot(self):
        """'1x 2011, 6x 2012...' lists vintages of ONE wine, not several
        wines -- vintage stays unset (can't pick one), mixed_lot is 0."""
        r, _ = _parse(
            "Burgund rot / MAISON X<br />Morey-St.-Denis 1er Aux Cheseaux: "
            "1x 2011, 6x 2012, 6x 2013, 2x 2015<br /><b>15 Flaschen</b>"
            "<br /><br />")
        self.assertIsNone(r["vintage"])
        self.assertFalse(r["mixed_lot"])

    def test_bare_br_champagne_style_with_bare_year_and_score(self):
        """No '<category> /' line at all; producer is just the first
        line; vintage has no 'Jahrgang:' prefix; a trailing critic score
        is noise, not part of the wine name."""
        r, errors = _parse(
            "<b>BOLLINGER</b><br>R.D. Extra Brut<br>2004<br>"
            "<b>2 Flaschen</b><br><br><b>RP97</b>")
        self.assertEqual(errors, [])
        self.assertEqual(r["producer"], "BOLLINGER")
        self.assertEqual(r["wine"], "R.D. Extra Brut")
        self.assertEqual(r["vintage"], 2004)

    def test_bare_br_strips_trailing_tasting_note_blurb(self):
        """A 'Winebutler: ...' tasting-note paragraph is marketing prose
        appended after the structured fields, never wine-identifying."""
        r, _ = _parse(
            "<b>CHATEAU CHASSE-SPLEEN</b><br>2009<br>"
            "<b>6 Magnums 1.5L</b><br><br>OHK<br><b></b>"
            '<p class="small mb-0"><br><b>Winebutler:</b><br>'
            "Der 2009er Château Chasse-Spleen präsentiert sich in tiefem "
            "Purpur...</p>")
        self.assertEqual(r["wine"], "CHATEAU CHASSE-SPLEEN")
        self.assertTrue(r["is_ohk"])
        self.assertEqual((r["quantity"], r["bottle_size_dl"]), (6, 15.0))

    def test_cm_condition_note_alone_is_discarded(self):
        r, _ = _parse(
            "<b>ARMAND ROUSSEAU</b><br>1991<br><b>1 Flasche</b><br><br>"
            "1.5cm<br><b></b>")
        self.assertEqual(r["wine"], "ARMAND ROUSSEAU")

    def test_no_quantity_still_reports_an_error(self):
        _, errors = _parse("Burgund rot / X<br />Some wine<br />")
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith("NO_QUANTITY"))

    def test_empty_description_is_an_error_not_a_crash(self):
        r, errors = _parse("")
        self.assertIsNone(r)
        self.assertEqual(len(errors), 1)


if __name__ == "__main__":
    unittest.main()
