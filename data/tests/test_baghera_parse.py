"""load_baghera: the live results-PDF row parser (_bag_parse_rows) and its
helpers, plus the legacy-JSON/live-PDF merge in load_baghera itself.

Lines are real, pulled from bagherawines.auction results PDFs (ids 25, 67,
100, 153; pdftotext -layout -enc UTF-8 output) -- not invented, each chosen
because it exercises a real formatting quirk found across those sales.
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402


class BagMoneyTest(unittest.TestCase):
    def test_straight_apostrophe_thousands_with_decimal(self):
        self.assertEqual(build_db._bag_money("7'320.00"), 7320.0)

    def test_curly_apostrophe_thousands_no_decimal(self):
        self.assertEqual(build_db._bag_money("3’600"), 3600.0)

    def test_rejects_comma_separated_tokens(self):
        """Confirmed real case: a multi-vintage lot description can end
        in a bare comma list like "13,14,15,17,18" -- this must never be
        mistaken for a price. to_float()'s own comma-handling would
        silently turn it into 17.18, so _bag_money has its own strict
        shape check instead of calling to_float on an unvalidated
        token."""
        self.assertIsNone(build_db._bag_money("13,14,15,17,18"))

    def test_rejects_unsold_marker(self):
        self.assertIsNone(build_db._bag_money("Unsold"))


class BagParseRowsTest(unittest.TestCase):
    def test_simple_sold_row_with_decimal_price(self):
        rows = build_db._bag_parse_rows(
            "  1      Château Lafite Rothschild - 1989             "
            "                                                   7'320.00\n")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["lot_no"], "1")
        self.assertEqual(row["description"],
                         "Château Lafite Rothschild - 1989")
        self.assertEqual(row["realised_price"], 7320.0)
        self.assertEqual(row["sold"], 1)

    def test_curly_apostrophe_thousands_no_decimal(self):
        rows = build_db._bag_parse_rows(
            "   26     Wine faucet                                      "
            "                 3’600\n")
        self.assertEqual(rows[0]["realised_price"], 3600.0)

    def test_explicit_unsold_marker(self):
        """Confirmed real case (a ~500-lot mixed-cellar sale): unsold
        lots print the literal word "Unsold" instead of a price."""
        rows = build_db._bag_parse_rows(
            "   505     Domaine Bizot, Vosne-Romanée “Les Jachées”"
            " 01,06,10,12                                           Unsold\n")
        row = rows[0]
        self.assertIsNone(row["realised_price"])
        self.assertEqual(row["sold"], 0)
        self.assertEqual(row["lot_no"], "505")

    def test_row_with_no_trailing_marker_at_all_falls_back_to_unsold(self):
        """Confirmed real case: in the same sale as the "Unsold" rows
        above, one row (502) has nothing at all in the price column --
        not even the word "Unsold" -- just trailing whitespace. It sits
        among otherwise-identical unsold neighbours, so this is treated
        the same as an explicit "Unsold", not dropped."""
        rows = build_db._bag_parse_rows(
            "   502     Domaine Bizot, Marsannay “Clos du Roy”"
            " 13,14,15,17,18                                          \n")
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["lot_no"], "502")
        self.assertTrue(row["description"].endswith("13,14,15,17,18"))
        self.assertIsNone(row["realised_price"])
        self.assertEqual(row["sold"], 0)

    def test_header_and_total_footer_lines_are_not_rows(self):
        rows = build_db._bag_parse_rows(
            "LOT N°                LOT DESCRIPTION             "
            "RESULT (CHF)\n"
            "         TOTAL                                      "
            "8’487’174\n"
            "                                        PAGE 1 OF 4\n")
        self.assertEqual(rows, [])


class BagTitleTest(unittest.TestCase):
    def test_first_non_blank_line_is_the_title(self):
        self.assertEqual(
            build_db._bag_title("\n\n   A beautiful day\n sale results\n"),
            "A beautiful day")


class LoadBagheraTest(unittest.TestCase):
    def _run(self, archive_dir):
        conn = __import__("sqlite3").connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        old = build_db.ARCHIVE
        build_db.ARCHIVE = archive_dir
        try:
            build_db.load_baghera(builder, None)
        finally:
            build_db.ARCHIVE = old
        conn.commit()
        return conn

    def test_live_pdf_creates_auction_with_hammer_plus_premium_basis(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Baghera", "live"))
            pdf = os.path.join(d, "Baghera", "live",
                                "180_20260707_results.pdf")
            open(pdf, "w").close()
            fake_text = (
                "Kipling#17\n sale results\n"
                "LOT N°      LOT DESCRIPTION           RESULT (CHF)\n"
                "   1      Some Wine - 2020                      500.00\n")
            with mock.patch.object(build_db, "_wermuth_pdf_text",
                                   return_value=fake_text):
                conn = self._run(d)
            row = conn.execute(
                "SELECT auction_date, price_basis FROM auctions").fetchone()
            self.assertEqual(row, ("2026-07-07", "HAMMER_PLUS_BUYERS_PREMIUM"))
            lot = conn.execute(
                "SELECT price_basis, realised_price, sold FROM lots"
            ).fetchone()
            self.assertEqual(lot, ("HAMMER_PLUS_BUYERS_PREMIUM", 500.0, 1))

    def test_live_pdf_for_an_already_legacy_id_is_skipped(self):
        """Defensive dedup beyond the ingest manifest: a live PDF must
        never double-load an id already covered by the legacy JSON
        archive."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Baghera", "2018", "06_Juni"))
            os.makedirs(os.path.join(d, "Baghera", "live"))
            legacy = os.path.join(
                d, "Baghera", "2018", "06_Juni", "auction-25.json")
            with open(legacy, "w", encoding="utf-8") as fh:
                fh.write(
                    '{"auction": {"id": 25, "title": "Legacy", "year": '
                    '2018, "month": 6, "currency": "CHF"}, "lots": '
                    '[{"lot_no": 1, "hammer": 100, "buyer_premium": 22, '
                    '"total_price": 122}]}')
            live_dupe = os.path.join(d, "Baghera", "live",
                                     "25_20180601_results.pdf")
            open(live_dupe, "w").close()
            with mock.patch.object(
                    build_db, "_wermuth_pdf_text",
                    return_value=("   1  Dupe Wine         999.00\n")):
                conn = self._run(d)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM auctions").fetchone()[0],
                1)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0], 1)

    def test_pdf_with_no_parseable_rows_creates_no_auction(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Baghera", "live"))
            pdf = os.path.join(d, "Baghera", "live",
                                "199_20261101_results.pdf")
            open(pdf, "w").close()
            with mock.patch.object(build_db, "_wermuth_pdf_text",
                                   return_value="no lot table here"):
                conn = self._run(d)
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM auctions").fetchone()[0],
                0)


if __name__ == "__main__":
    unittest.main()
