"""load_denz_wermuth: tail parsing shared by both eras, the sticky-header
catalog parser, the self-contained result-line parser, and date/catalog-
number extraction.

Examples are real, pulled from the archive (not invented), each chosen
because it broke an earlier version of the parser.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


class WermuthTailTest(unittest.TestCase):
    def test_full_result_line(self):
        rest, qty, dl, vintage, is_ohk, lo, hi, hammer = (
            build_db._wermuth_parse_tail(
                "Château Sociando Mallet      1 Dutzend Flaschen, 1995, "
                "6er OHK   pro Dz.   Sfr. 480-600     SFr.     500.00"))
        self.assertEqual(rest, "Château Sociando Mallet")
        self.assertEqual((qty, dl, vintage), (12, 7.5, 1995))
        self.assertTrue(is_ohk)
        self.assertEqual((lo, hi, hammer), (480.0, 600.0, 500.0))

    def test_catalog_line_has_no_result(self):
        """A pre-sale catalog line has an estimate but never a result --
        the SAME tail parser just returns hammer=None for it."""
        rest, qty, dl, vintage, is_ohk, lo, hi, hammer = (
            build_db._wermuth_parse_tail(
                "1 Dutzend Flaschen, 1994, OHK pro Dz. Sfr. 1680-2100"))
        self.assertEqual(rest, "")
        self.assertEqual((qty, dl, vintage), (12, 7.5, 1994))
        self.assertTrue(is_ohk)
        self.assertEqual((lo, hi, hammer), (1680.0, 2100.0, None))

    def test_eighth_bottle_fraction_space_joined(self):
        """'12 3/8-Flaschen' is the common form, but '12 3/8 Flaschen'
        (space, not hyphen, before the unit) is also real -- missing
        either joiner used to make the fraction fall through unmatched
        and misread the denominator ("8") as the quantity instead."""
        rest, qty, dl, *_ = build_db._wermuth_parse_tail(
            "Château Lagrange, AC/MC, St. Julien, 3e grand      "
            "12 3/8 Flaschen, 2005, OHK   pro Lot CHF 300-420     "
            "CHF   300.00")
        self.assertEqual((qty, dl), (12, 3.75))
        self.assertIn("Château Lagrange", rest)
        self.assertNotIn("3/", rest)

    def test_eighth_bottle_fraction_hyphen_joined(self):
        rest, qty, dl, *_ = build_db._wermuth_parse_tail(
            "12 3/8-Flaschen 1989 pro Lot Sfr. 300-420")
        self.assertEqual((qty, dl), (12, 3.75))

    def test_dutzend_is_a_quantity_multiplier_not_a_unit(self):
        """'1 Dutzend Flaschen' = 1 dozen = 12 standard bottles, not 1
        bottle labelled 'Dutzend'."""
        _, qty, dl, *_ = build_db._wermuth_parse_tail(
            "2 Dutzend Flaschen, 1990 pro Dz. Sfr. 100-200")
        self.assertEqual((qty, dl), (24, 7.5))

    def test_backwards_estimate_range_is_a_source_truncation_not_fixable(self):
        """The source PDF literally prints "Sfr. 2100-300" (a narrow
        column truncates the high estimate's last digit) -- not
        recoverable, and a backwards range is worse than none."""
        _, _, _, _, _, lo, hi, _ = build_db._wermuth_parse_tail(
            "3 Flaschen, 1996, OHK pro Lot Sfr. 2100-300")
        self.assertIsNone(lo)
        self.assertIsNone(hi)

    def test_unsold_dash_result_is_no_price(self):
        *_, hammer = build_db._wermuth_parse_tail(
            "6 Flaschen, 2001                        pro Lot   "
            "Sfr. 240-330      SFr.        -")
        self.assertIsNone(hammer)


class WermuthWineDescTest(unittest.TestCase):
    def test_four_part_desc(self):
        wine, producer, region, cls = build_db._wermuth_split_wine_desc(
            "Dom Pérignon, AC/MO, Champagne, Moët & Chandon")
        self.assertEqual(wine, "Dom Pérignon")
        self.assertEqual(producer, "Moët & Chandon")
        self.assertEqual(region, "Champagne")
        self.assertEqual(cls, "AC/MO")

    def test_bare_chateau_name_defaults_producer_to_itself(self):
        wine, producer, region, cls = build_db._wermuth_split_wine_desc(
            "Château Sociando Mallet")
        self.assertEqual(wine, "Château Sociando Mallet")
        self.assertEqual(producer, "Château Sociando Mallet")

    def test_classification_rank_is_not_mistaken_for_a_producer(self):
        """'5e grand cru classé' sits in the SAME trailing comma slot a
        real producer (e.g. "Mondavi") would -- only a known
        classification phrase there is redirected, not every value.
        Producer still ends up filled, but via the estate-name fallback
        below, not by keeping the classification text as if it named
        a producer."""
        wine, producer, region, cls = build_db._wermuth_split_wine_desc(
            "Château Grand Puy Lacoste, AC/MC, Pauillac, 5e grand cru "
            "classé")
        self.assertEqual(producer, "Château Grand Puy Lacoste")
        self.assertEqual(cls, "AC/MC, 5e grand cru classé")
        self.assertEqual(region, "Pauillac")

    def test_real_three_part_producer_is_kept(self):
        wine, producer, region, cls = build_db._wermuth_split_wine_desc(
            "Cabernet Sauvignon, MO, Kalifornien, Mondavi")
        self.assertEqual(producer, "Mondavi")
        self.assertEqual(region, "Kalifornien")

    def test_embedded_code_with_no_comma_before_it(self):
        """Usually '<wine>, <code>, <region>...' -- but on some files the
        comma before the code is simply missing, gluing it onto the wine
        name itself."""
        wine, producer, region, cls = build_db._wermuth_split_wine_desc(
            "Château Rol Valentin                      AC/ MC, "
            "St. Emilion, grand cru")
        self.assertEqual(wine, "Château Rol Valentin")
        self.assertEqual(producer, "Château Rol Valentin")
        self.assertEqual(region, "St. Emilion")

    def test_trailing_total_word_is_stripped(self):
        wine, *_ = build_db._wermuth_split_wine_desc(
            "Noon Eclipse                      Total")
        self.assertEqual(wine, "Noon Eclipse")

    def test_mixlot_prefix_is_not_special_cased_here(self):
        """mixed_lot is set by the caller from the raw wine text, not by
        this splitter -- it just needs to leave the "Mixlot" prefix
        intact for that check."""
        wine, *_ = build_db._wermuth_split_wine_desc("Mixlot Bordeaux")
        self.assertEqual(wine, "Mixlot Bordeaux")


class WermuthCatalogPdfTest(unittest.TestCase):
    def test_sticky_header_applies_to_following_lots(self):
        text = (
            " Château Mouton-Rothschild\n"
            " AC/MC, Pauillac\n"
            " 2 1 Dutzend Flaschen, 1990, OHK pro Dz. Sfr. 2300-2700\n"
            " 3 1 Dutzend Flaschen, 1983, OHK pro Dz. Sfr. 2600-3300\n")
        lots = list(build_db._wermuth_parse_catalog_pdf(text))
        self.assertEqual(len(lots), 2)
        for lot in lots:
            self.assertEqual(lot["wine"], "Château Mouton-Rothschild")
            self.assertEqual(lot["region"], "Pauillac")

    def test_three_part_header_with_real_producer(self):
        text = (
            " Cabernet Sauvignon\n"
            " MO, Kalifornien, Mondavi\n"
            " 49 10 Flaschen, 1997, OHK pro Lot Sfr. 350-500\n")
        lots = list(build_db._wermuth_parse_catalog_pdf(text))
        self.assertEqual(lots[0]["producer"], "Mondavi")
        self.assertEqual(lots[0]["region"], "Kalifornien")

    def test_three_part_header_with_classification_not_producer(self):
        text = (
            " Château Grand Puy Lacoste\n"
            " AC/MC, Pauillac, 5e grand cru classé\n"
            " 840 1 Dutzend Flaschen, 1996, OHK pro Dz. Sfr. 960-1200\n")
        lots = list(build_db._wermuth_parse_catalog_pdf(text))
        self.assertEqual(lots[0]["producer"], "Château Grand Puy Lacoste")
        self.assertEqual(lots[0]["classification"], "5e grand cru classé")

    def test_header_without_a_region_line_at_all(self):
        """Some wines go straight from name to lot line, no header2 --
        producer stays unset unless the name itself is an estate."""
        text = (
            " Nonino Grappa Collezione 1999 il corpo\n"
            " 46 1 Flasche, 1990 OHK pro Lot Sfr. 500-1000\n")
        lots = list(build_db._wermuth_parse_catalog_pdf(text))
        self.assertEqual(lots[0]["wine"], "Nonino Grappa Collezione 1999 il corpo")

    def test_page_footer_lines_are_not_mistaken_for_a_new_wine_header(self):
        text = (
            " Château Cheval Blanc\n"
            " AC/MC, St. Emilion grand cru classé\n"
            "file:///Users/marcopersi/Google%20Drive/Wein/Wermuth/2003/"
            "WZ_156.html    Seite 1 von 26\n"
            "\x0cWZ-156-1                                09.08.14 15:12\n"
            " 1 1 Dutzend Flaschen, 1994, OHK pro Dz. Sfr. 1680-2100\n")
        lots = list(build_db._wermuth_parse_catalog_pdf(text))
        self.assertEqual(len(lots), 1)
        self.assertEqual(lots[0]["wine"], "Château Cheval Blanc")

    def test_bare_date_html_footer_with_no_form_feed_or_file_prefix(self):
        """The VERY FIRST page-footer occurrence (top of file, not a page
        break) has neither the "\\x0c" nor the "file:///" marker the
        later repeats do -- only ".html" is common to all of them."""
        text = (
            "8/25/2014                                    WZ_169.html\n"
            " Château Something\n"
            " AC/MC, Pauillac\n"
            " 1 6 Flaschen, 2000 pro Lot Sfr. 100-200\n")
        lots = list(build_db._wermuth_parse_catalog_pdf(text))
        self.assertEqual(lots[0]["wine"], "Château Something")


class WermuthResultPdfTest(unittest.TestCase):
    def test_self_contained_line(self):
        text = (
            "     1 Château Sociando Mallet      1 Dutzend Flaschen, 1995, "
            "6er OHK   pro Dz.   Sfr. 480-600     SFr.     500.00\n")
        lots = list(build_db._wermuth_parse_result_pdf(text))
        self.assertEqual(len(lots), 1)
        lot = lots[0]
        self.assertEqual(lot["wine"], "Château Sociando Mallet")
        self.assertEqual(lot["hammer_price"], 500.0)

    def test_no_result_means_not_a_lot(self):
        """Unlike the catalog parser, a line with no result here is
        either a genuinely unsold lot (dash) or not a lot line at all --
        either way there is nothing to load."""
        text = "6 Flaschen, 2001 pro Lot Sfr. 240-330 SFr. -\n"
        self.assertEqual(list(build_db._wermuth_parse_result_pdf(text)), [])

    def test_mixlot_prefix_sets_mixed_lot(self):
        text = ("164 Mixlot Champagne, AC/MO, Champagne, Moët & Chandon  "
                "3 Flaschen, 2004, OHK pro Lot Sfr. 300-400 SFr. 350.00\n")
        lots = list(build_db._wermuth_parse_result_pdf(text))
        self.assertEqual(lots[0]["mixed_lot"], 1)


class WermuthDateAndCatalogNumberTest(unittest.TestCase):
    def test_wz_prefixed_filename(self):
        self.assertEqual(
            build_db._wermuth_catalog_number("Wermuth_WZ-156.pdf"), "156")
        self.assertEqual(
            build_db._wermuth_catalog_number("WZ-229_Resultate.pdf"), "229")

    def test_bare_leading_number_followed_by_underscore(self):
        """Regression: \\b never holds between a digit and "_" (both are
        \\w), so "265_Resultate Web.pdf" silently failed to match and
        fell back to the whole filename as the catalog number --
        splitting one real auction across two different auction_ids."""
        self.assertEqual(
            build_db._wermuth_catalog_number("265_Resultate Web.pdf"),
            "265")
        self.assertEqual(
            build_db._wermuth_catalog_number("280_Nachverkaufsliste.pdf"),
            "280")

    def test_date_from_filename_ddmmyyyy(self):
        self.assertEqual(
            build_db._wermuth_date_from_filename(
                "WZ-255_14112015_Resultate.pdf"),
            "2015-11-14")

    def test_date_from_text_german_month(self):
        self.assertEqual(
            build_db._wermuth_date_from_text(
                "Donnerstag, 12.April 2012\nWeinauktion"),
            "2012-04-12")

    def test_date_from_text_with_no_space_before_month(self):
        self.assertEqual(
            build_db._wermuth_date_from_text("Samstag, 1. März 2003"),
            "2003-03-01")


if __name__ == "__main__":
    unittest.main()
