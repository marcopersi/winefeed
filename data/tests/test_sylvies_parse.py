"""sylvies loaders: month-key parsing, vintage/description/bottle/result
parsing shared by both sources, and the HTML multi-wine-lot combiner.

Examples are real, pulled from the archive (not invented), each chosen
because it broke an earlier version of the parser.
"""
import os
import sys
import unittest

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


def _html_item(inner):
    return BeautifulSoup(
        f'<div class="auction_item">{inner}</div>', "html.parser"
    ).find("div", class_="auction_item")


class SylviesMonthKeyTest(unittest.TestCase):
    def test_english_and_german_month_names(self):
        self.assertEqual(build_db._sylvies_month_key("February2012.zip"),
                         ("2012", 2))
        self.assertEqual(build_db._sylvies_month_key("Februar2024.txt"),
                         ("2024", 2))
        self.assertEqual(build_db._sylvies_month_key("Dezember2023.txt"),
                         ("2023", 12))
        self.assertEqual(build_db._sylvies_month_key("december2022.txt"),
                         ("2022", 12))

    def test_unrecognized_name_returns_none(self):
        self.assertIsNone(build_db._sylvies_month_key("sylviesParser.py"))

    def test_known_typo_year_is_corrected(self):
        """Three 2018 files are the only copy of their month under a
        typo'd 5-digit year ("August20218.txt") -- not a duplicate of a
        correctly-named file, so this can't just be skipped."""
        self.assertEqual(build_db._sylvies_month_key("August20218.txt"),
                         ("2018", 8))

    def test_unknown_5digit_year_returns_none(self):
        self.assertIsNone(build_db._sylvies_month_key("August20219.txt"))


class SylviesVintageTest(unittest.TestCase):
    def test_leading_year_stripped(self):
        self.assertEqual(
            build_db._sylvies_extract_vintage("1998 Gevrey Chambertin"),
            (1998, "Gevrey Chambertin"))

    def test_no_year_nv_wine(self):
        self.assertEqual(
            build_db._sylvies_extract_vintage("Brut 'Grande Cuvee'"),
            (None, "Brut 'Grande Cuvee'"))


class SylviesDescriptionTest(unittest.TestCase):
    def test_region_producer_split(self):
        self.assertEqual(
            build_db._sylvies_split_description("Italy | la Stoppa"),
            ("Italy", "la Stoppa"))

    def test_bare_mc_is_a_bottling_code_not_a_producer(self):
        """'Mc' (mise en bouteille au château) is the single most common
        value in this field (~90k of ~260k lots) -- it names how the wine
        was bottled, not who made it. Storing it as producer would flood
        the producer index with one meaningless bucket."""
        region, producer = build_db._sylvies_split_description(
            "Medoc | Mc")
        self.assertEqual(region, "Medoc")
        self.assertIsNone(producer)

    def test_bare_neg_and_dom_and_dist_are_also_codes(self):
        for code in ("Neg", "Neg.", "Dom", "Dom.", "Dist", "Dist."):
            with self.subTest(code=code):
                _, producer = build_db._sylvies_split_description(
                    f"Bordeaux | {code}")
                self.assertIsNone(producer)

    def test_named_negociant_is_kept(self):
        """'Neg. Jean Theil' names a real merchant -- only the BARE code
        is a placeholder, not every string containing it."""
        _, producer = build_db._sylvies_split_description(
            "Saint Julien | Neg. Jean Theil")
        self.assertEqual(producer, "Neg. Jean Theil")

    def test_no_pipe_keeps_whole_text_as_region(self):
        region, producer = build_db._sylvies_split_description("Italy")
        self.assertEqual(region, "Italy")
        self.assertIsNone(producer)


class SylviesBottleTest(unittest.TestCase):
    def test_named_bottle_with_ohk_marker(self):
        self.assertEqual(
            build_db._sylvies_parse_bottle("12 Bottle(s), Oc"),
            (12, 7.5, True))

    def test_named_magnum_no_marker(self):
        self.assertEqual(
            build_db._sylvies_parse_bottle("1 Magnum"),
            (1, 15.0, False))

    def test_explicit_liters_half_bottle(self):
        self.assertEqual(
            build_db._sylvies_parse_bottle("12 x 0,5 Ltr, Oc"),
            (12, 5.0, True))

    def test_explicit_liters_overrides_named_default(self):
        """'1 x 3.00 Ltr' is an explicit double-magnum-sized bottle --
        trust the stated liters over any named-format guess."""
        self.assertEqual(
            build_db._sylvies_parse_bottle("1 x 3.00 Ltr, Owc"),
            (1, 30.0, True))

    def test_dash_suffixed_marker_is_still_recognized(self):
        """'Owc-1'/'Oc-2' (a numbered-case suffix) is the MORE common
        form in this archive (44,557 hits vs. plain Oc/Owc) -- only the
        part before the dash is the actual marker."""
        self.assertEqual(
            build_db._sylvies_parse_bottle("1 x 6.00 Ltr, Owc-1"),
            (1, 60.0, True))
        self.assertEqual(
            build_db._sylvies_parse_bottle("12 Bottle(s), Oc-2"),
            (12, 7.5, True))

    def test_unrecognized_marker_does_not_set_ohk(self):
        """An allowlist, not a blocklist -- only Oc/Owc flag is_ohk, so
        source drift in the marker text can't cause a false positive."""
        qty, dl, is_ohk = build_db._sylvies_parse_bottle("3 Bottle(s), 0")
        self.assertEqual((qty, dl), (3, 7.5))
        self.assertFalse(is_ohk)

    def test_unparseable_text_returns_all_none(self):
        self.assertEqual(build_db._sylvies_parse_bottle("???"),
                         (None, None, False))


class SylviesResultTest(unittest.TestCase):
    def test_clean_price(self):
        self.assertEqual(build_db._sylvies_parse_result("€ 170"),
                         (170.0, 1))

    def test_not_been_sold_text(self):
        self.assertEqual(
            build_db._sylvies_parse_result("This lot has not been sold."),
            (None, 0))

    def test_scraper_bug_bare_next_lot_number(self):
        """The txt capture's scraper bug: an unsold lot's Result field
        becomes the FOLLOWING lot's bare number (find_next("p") ran past
        the unsold text node into the next auction_item). Confirmed on a
        full file: every such bare digit equals the next block's lot
        number -- resolves the same as a clean "not sold," not as a
        price, regardless of which number it happens to be."""
        self.assertEqual(build_db._sylvies_parse_result("52"), (None, 0))

    def test_rare_untyped_garbage(self):
        self.assertEqual(
            build_db._sylvies_parse_result("Italiëlei 21,"), (None, 0))


class SylviesEstimateTest(unittest.TestCase):
    def test_range(self):
        self.assertEqual(
            build_db._sylvies_parse_estimate("€ 140 - € 220"),
            (140.0, 220.0))

    def test_missing(self):
        self.assertEqual(build_db._sylvies_parse_estimate(""), (None, None))


class SylviesTxtBlockTest(unittest.TestCase):
    def test_blank_bottletype_line_does_not_leak_into_next_field(self):
        """Regression: [ \\t]* not \\s* in the field regex -- \\s matches
        the newline too, so a blank "Lot Bottletype: " line let the match
        spill over and capture the next line's "Estimate: ..." text."""
        block = (
            "\nLot Number: 436\n"
            "Lot Name: 2009 Chateau la Tour de By\n"
            "Lot Description: Medoc | Mc\n"
            "Lot Bottle: 1 x 6.00 Ltr, Owc\n"
            "Lot Bottletype: \n"
            "Estimate: € 130 - € 170\n"
            "Result: € 130\n"
            "Lot My Bid: N/A\n")
        row = build_db._sylvies_parse_txt_block(block)
        self.assertIsNone(row["condition_text"])
        self.assertEqual(row["estimate_low"], 130.0)

    def test_vat_lot_marker_line(self):
        block = (
            "Lot Number: 1\n\nVAT LOT\n"
            "Lot Name: 1998 Gevrey Chambertin\n"
            "Lot Description: 1er Cru | Harmand Geoffroy\n"
            "Lot Bottle: 12 Bottle(s), Oc\n"
            "Lot Bottletype: \n"
            "Estimate: € 140 - € 200\n"
            "Result: € 170\n"
            "Lot My Bid: N/A\n")
        row = build_db._sylvies_parse_txt_block(block)
        self.assertEqual(row["note"], "VAT LOT")
        self.assertEqual(row["mixed_lot"], None)  # unrecoverable from txt

    def test_no_lot_number_is_not_a_lot(self):
        self.assertIsNone(build_db._sylvies_parse_txt_block("garbage\n"))


# Real markup pulled from the archive (February2012.zip, Resultatfile4.html).
_SINGLE_WINE_ITEM = """
<div class="row">
  <div class="large-8 columns">
    <p class="lot_nr"><a>78</a></p>
    <div class="lot_item lot_wine_1">
      <div class="lot_name"><a>1990 Something</a></div>
      <div class="lot_description">France | Dom X</div>
      <div class="lot_bottle">6 Bottle(s), Owc</div>
      <div class="lot_bottle_type"></div>
    </div>
  </div>
  <div class="large-2 columns auction_infos">
    <div><div class="lot_estimate">Estimate</div><p>€ 300 - € 500</p></div>
    <div><div class="lot_my_bid">Result</div><p>€ 410</p></div>
  </div>
</div>
"""

_UNSOLD_ITEM = """
<div class="row">
  <div class="large-8 columns">
    <p class="lot_nr"><a>77</a></p>
    <div class="lot_item lot_wine_1">
      <div class="lot_name"><a>1998 Cabernet Sauvignon 'Stoppa'</a></div>
      <div class="lot_description">Italy | la Stoppa</div>
      <div class="lot_bottle">7 Bottle(s), Oc</div>
      <div class="lot_bottle_type"></div>
    </div>
    <div class="lot_item lot_wine_1">
      <div class="lot_name"><a>2003 Cabernet Sauvignon 'Stoppa'</a></div>
      <div class="lot_description">Italy | la Stoppa</div>
      <div class="lot_bottle">5 Bottle(s)</div>
      <div class="lot_bottle_type"></div>
    </div>
  </div>
  <div class="large-2 columns auction_infos">
    <div><div class="lot_estimate">Estimate</div><p>€ 140 - € 220</p></div>
    <div><div class="lot_my_bid">Result</div>This lot has not been sold.</div>
  </div>
</div>
"""


class SylviesHtmlItemTest(unittest.TestCase):
    def test_single_wine_lot(self):
        row = build_db._sylvies_parse_html_item(_html_item(_SINGLE_WINE_ITEM))
        self.assertEqual(row["lot_no"], "78")
        self.assertEqual(row["wine"], "Something")
        self.assertEqual(row["vintage"], 1990)
        self.assertEqual(row["producer"], "Dom X")
        self.assertEqual(row["region"], "France")
        self.assertEqual((row["quantity"], row["bottle_size_dl"]), (6, 7.5))
        self.assertTrue(row["is_ohk"])
        self.assertEqual(row["hammer_price"], 410.0)
        self.assertEqual(row["sold"], 1)
        self.assertIsNone(row["mixed_lot"])

    def test_unsold_result_is_a_bare_text_node_not_a_p_tag(self):
        """Regression: find_next("p") (the scraper's own bug) would skip
        this bare text node and grab an unrelated <p> elsewhere in the
        page; this loader reads the parent's own text instead."""
        row = build_db._sylvies_parse_html_item(_html_item(_UNSOLD_ITEM))
        self.assertIsNone(row["hammer_price"])
        self.assertEqual(row["sold"], 0)

    def test_two_wine_lot_combines_and_flags_mixed(self):
        row = build_db._sylvies_parse_html_item(_html_item(_UNSOLD_ITEM))
        self.assertEqual(row["mixed_lot"], 1)
        self.assertIn("Cabernet Sauvignon 'Stoppa'", row["wine"])
        self.assertEqual(row["producer"], "la Stoppa")  # agrees across subs
        self.assertEqual(row["region"], "Italy")
        self.assertEqual(row["quantity"], 12)  # 7 + 5
        self.assertTrue(row["is_ohk"])  # true if ANY sub-item is OHK

    def test_no_lot_nr_is_not_a_lot(self):
        self.assertIsNone(build_db._sylvies_parse_html_item(
            _html_item("<div></div>")))


if __name__ == "__main__":
    unittest.main()
