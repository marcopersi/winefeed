"""load_franzwermuth: the results-PDF row parser (_fw_parse_rows) and its
money/marker helpers.

Lines are real, pulled from franzwermuth.ch's Collection 17 results PDF
(pdftotext -layout -enc UTF-8 output), not invented -- each chosen
because it broke an earlier version of the parser.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


class LoadFranzwermuthTest(unittest.TestCase):
    def test_catalog_only_pdf_does_not_create_a_phantom_auction(self):
        """Confirmed real case: the archive mixes pre-sale catalog
        PDFs in with results PDFs (e.g. Collections 12/19 only have a
        "..._Katalog.pdf", no results file at all) -- a catalog has no
        Zuschlag column, so it must not create a 0-lot auction row."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "FranzWermuth", "2020"))
            katalog = os.path.join(
                d, "FranzWermuth", "2020", "Coll12_Katalog.pdf")
            open(katalog, "w").close()
            conn = __import__("sqlite3").connect(":memory:")
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                with mock.patch.object(
                        build_db, "_wermuth_pdf_text",
                        return_value="no results table here"):
                    build_db.load_franzwermuth(builder, None)
            finally:
                build_db.ARCHIVE = old
            conn.commit()
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM auctions").fetchone()[0],
                0)

    def test_second_file_for_an_already_loaded_collection_is_skipped(self):
        """Confirmed real case: Collection 6 has both a catalog PDF and
        a results PDF side by side -- the results file must not be
        double-counted if a second real-results file for the same
        collection number is ever found."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "FranzWermuth", "2017"))
            for name in ("Coll6_Ergebnisliste.pdf", "Coll6_Ergebnis2.pdf"):
                open(os.path.join(d, "FranzWermuth", "2017", name),
                     "w").close()
            conn = __import__("sqlite3").connect(":memory:")
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                with mock.patch.object(
                        build_db, "_wermuth_pdf_text",
                        return_value=(
                            "   1 Some Wine  2020 1 Flasche  Lot  CHF "
                            "100-150  120,00 CHF\n")):
                    build_db.load_franzwermuth(builder, None)
            finally:
                build_db.ARCHIVE = old
            conn.commit()
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM auctions").fetchone()[0],
                1)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0], 1)


class FranzWermuthParseTest(unittest.TestCase):
    def test_simple_row(self):
        rows = build_db._fw_parse_rows(
            "Lot Objekt/Wein                                        Jg.   "
            "Menge             Verp. Lot/Dz. Schätzung      Zuschlag\n"
            "   1 Château Palmer St. Julien, 3ème grand cru classé  2001 "
            "5 Flaschen                Lot   CHF 1000-1250      "
            "850,00 CHF\n")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["lot_no"], "1")
        self.assertEqual(row["wine"],
                         "Château Palmer St. Julien, 3ème grand cru classé")
        self.assertEqual(row["vintage"], 2001)
        self.assertEqual(row["quantity"], 5)
        self.assertEqual(row["bottle_size_dl"], 7.5)
        self.assertFalse(row["is_ohk"])
        self.assertEqual((row["estimate_low"], row["estimate_high"]),
                         (1000.0, 1250.0))
        self.assertEqual(row["hammer_price"], 850.0)
        self.assertEqual(row["price_basis"], "HAMMER")

    def test_dutzend_and_ohk_before_dz_marker(self):
        """Confirmed real case: "1 Dutzend Flaschen OHK Dz." -- OHK sits
        between the unit word and the Lot/Dz. marker, not at the very
        end, so it must be stripped before the quantity regex (which
        is anchored to the end of what's left) ever sees it."""
        rows = build_db._fw_parse_rows(
            "   2 Château Gruaud Larose St. Julien, 2ème grand cru classé "
            "2003 1 Dutzend Flaschen OHK Dz.      CHF 720-900        "
            "800,00 CHF\n")
        row = rows[0]
        self.assertEqual(row["quantity"], 12)
        self.assertTrue(row["is_ohk"])
        self.assertEqual(row["hammer_price"], 800.0)

    def test_wrapped_row_spans_two_physical_lines(self):
        """Confirmed real case: a long description pushes the "Lot/Dz.
        CHF ..." tail onto its own pdftotext -layout line (real lines
        23/24 of the Collection 17 PDF)."""
        rows = build_db._fw_parse_rows(
            "  20 Domaine de Chevalier , Pessac-Léognan, gccl. (rouge) "
            "1990 6 Flaschen          12er-OHK\n"
            "                                                          "
            "        Lot   CHF 720-900        660,00 CHF\n")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["lot_no"], "20")
        self.assertEqual(row["quantity"], 6)
        self.assertTrue(row["is_ohk"])
        self.assertEqual(row["hammer_price"], 660.0)

    def test_unsold_lot_has_dash_instead_of_price(self):
        """Confirmed real case: an unsold lot's hammer field is a
        literal "-", not a number."""
        rows = build_db._fw_parse_rows(
            " 109 Cabernet Sauvignon “Gregory Vineyard”, Sonoma"
            "        Div. 11 Flaschen              Lot   CHF 550-900"
            "        - CHF\n")
        row = rows[0]
        self.assertIsNone(row["vintage"])  # "Div." = mixed vintages
        self.assertIsNone(row["hammer_price"])
        self.assertEqual(row["price_basis"], "UNKNOWN")

    def test_oc_marker_replaces_lot_dz_column_entirely(self):
        """Confirmed real case (lots 127-132): the condition marker
        "OC" sometimes stands in for the Lot/Dz. marker instead of
        appearing alongside it -- no "Lot"/"Dz." token at all on these
        rows."""
        rows = build_db._fw_parse_rows(
            " 127 Domaine A “Cabernet Sauvignon” , Tasm., "
            "Dom. Althaus       2009 6 Flaschen             OC    "
            "CHF 420-600          - CHF\n")
        row = rows[0]
        self.assertEqual(row["quantity"], 6)
        self.assertTrue(row["is_ohk"])

    def test_fehlt_marker_with_no_trailing_chf(self):
        """Confirmed real case (lots 334-336): a withdrawn-after-
        catalog lot's result is the word "fehlt" ("missing"), with no
        trailing "CHF" at all on that line."""
        rows = build_db._fw_parse_rows(
            " 334 Beaune “Grèves”, Côte de Beaune "
            "1er cru, Thomas Morey   2018 6 Flaschen         OC Lot    "
            "CHF 180-600     fehlt\n")
        row = rows[0]
        self.assertIsNone(row["hammer_price"])
        self.assertEqual(row["price_basis"], "UNKNOWN")

    def test_vintage_glued_to_preceding_word_with_no_space(self):
        """Confirmed real case (lot 369): a pdftotext layout glitch
        drops the space before the vintage ("Vill.2015" instead of
        "Vill. 2015")."""
        rows = build_db._fw_parse_rows(
            " 369 Thunevin-Calvet “Les Trois Marie”, "
            "Côtes du Roussillon Vill.2015 6 Flaschen        "
            "6er-OHK Lot   CHF 450-540     370,00 CHF\n")
        row = rows[0]
        self.assertEqual(row["vintage"], 2015)
        self.assertEqual(row["hammer_price"], 370.0)

    def test_fw_money_period_thousands_comma_decimal(self):
        self.assertEqual(build_db._fw_money("1.050,00"), 1050.0)
        self.assertEqual(build_db._fw_money("850,00"), 850.0)
        self.assertIsNone(build_db._fw_money("-"))
        self.assertIsNone(build_db._fw_money("fehlt"))

    def test_fw_money_apostrophe_thousands_separator(self):
        """Confirmed real case (Collection 16, 2022 era): the hammer
        price column uses an apostrophe thousands separator ("1'990
        CHF"), not a period or space -- must not be left over for
        to_float to choke on."""
        self.assertEqual(build_db._fw_money("1'990"), 1990.0)
        rows = build_db._fw_parse_rows(
            "   5 Château Palmer, Margaux, 3ème grand cru classé "
            "1994    1 Dutzend Flaschen          CHF 1800-2400         "
            "1'990 CHF\n")
        row = rows[0]
        self.assertEqual(row["hammer_price"], 1990.0)
        self.assertEqual(row["price_basis"], "HAMMER")

    def test_fw_money_space_thousands_separator(self):
        """Confirmed real case (Collection 6, 2017 era): this layout
        uses a SPACE as the thousands separator instead of a period
        ("1 840,00" CHF)."""
        self.assertEqual(build_db._fw_money("1 840,00"), 1840.0)

    def test_vintage_baked_into_wine_name_no_separate_column(self):
        """Confirmed real case (Collection 1, 2015 era): no vintage
        column at all -- the year is just part of the wine name text,
        and the hammer price is a bare number with no "CHF" anywhere
        on the line."""
        rows = build_db._fw_parse_rows(
            "   1 Château Figeac 1982                                  "
            "5 Flaschen               Lot    CHF 1000-1200     1050\n")
        row = rows[0]
        self.assertEqual(row["wine"], "Château Figeac")
        self.assertEqual(row["vintage"], 1982)
        self.assertEqual(row["hammer_price"], 1050.0)

    def test_vintage_comma_joined_after_quantity(self):
        """Confirmed real case (Collection 3, 2016 era): vintage comes
        AFTER the quantity+unit, comma-joined, instead of before it --
        and the hammer price is CHF-prefixed, not suffixed."""
        rows = build_db._fw_parse_rows(
            "   1 Château Canon La Gaffelière               "
            "6 Flaschen, 2002                             OHK Lot "
            "CHF 240-360       CHF     260,00\n")
        row = rows[0]
        self.assertEqual(row["wine"], "Château Canon La Gaffelière")
        self.assertEqual(row["vintage"], 2002)
        self.assertEqual(row["quantity"], 6)
        self.assertTrue(row["is_ohk"])
        self.assertEqual(row["hammer_price"], 260.0)

    def test_pro_marker_between_quantity_and_lot_dz(self):
        """Confirmed real case (Collections 5/6, 2017 era): the
        column header "pro" sits directly before "Lot"/"Dz" in the
        data row too ("1 Dutzend Flaschen OHK Dz" with no trailing
        period, "1 Magnumflasche pro Lot"), not just as a header
        label -- both must be stripped to reach the quantity text."""
        rows = build_db._fw_parse_rows(
            "   1 Château Chasse Spleen, 2003                     "
            "1 Dutzend Flaschen     OHK     Dz    CHF 330-480       "
            "CHF      300,00\n"
            "   2 Château Palmer 1990                        "
            "1 Magnumflasche               pro Lot   CHF 500-700     "
            "CHF        500,00\n")
        self.assertEqual(rows[0]["quantity"], 12)
        self.assertEqual(rows[0]["vintage"], 2003)
        self.assertEqual(rows[1]["quantity"], 1)
        self.assertEqual(rows[1]["bottle_size_dl"], 15.0)
        self.assertEqual(rows[1]["vintage"], 1990)


if __name__ == "__main__":
    unittest.main()
