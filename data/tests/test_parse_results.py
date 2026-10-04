import os
import tempfile
import unittest

from parse_results import (parse_hdh_pdf, parse_weinauktionator_xlsx)


class TestWeinauktionatorXlsx(unittest.TestCase):
    def test_parses_lots(self):
        import openpyxl

        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "results_39.xlsx")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(["Auktionsergebnisse: Sommerauktion 2026"])
            ws.append(["11.07.2026"])
            ws.append([])
            ws.append([])
            ws.append(["Lot", "Anbauregion", "Titel", "Versteigert für",
                       "Weine"])
            ws.append(["09967", "Alsace", "Trimbach, Clos Sainte Hune 2011",
                       "---   ", "3 x 0.750 ..."])
            ws.append(["09925", "Armagnac", "Laubade, Bas Armagnac 1936",
                       240.0, "1 x 0.700 ..."])
            wb.save(path)

            result = parse_weinauktionator_xlsx(path)
            self.assertEqual(result["auction"]["date"], "2026-07-11")
            self.assertEqual(len(result["lots"]), 2)
            self.assertIsNone(result["lots"][0]["hammer_price"])
            self.assertEqual(result["lots"][1]["hammer_price"], 240.0)
            self.assertEqual(result["lots"][1]["region"], "Armagnac")


class TestHdhHelpers(unittest.TestCase):
    def test_sale_year_month(self):
        from parse_results import _sale_year_month
        self.assertEqual(_sale_year_month("2609"), (2026, 9))

    def test_us_number(self):
        from parse_results import _us_number
        self.assertEqual(_us_number("10,157.50"), 10157.5)

    def test_lot_line(self):
        from parse_results import _LOT_LINE
        match = _LOT_LINE.match(
            "1 3 2005 Château Le Pin 6,500 - 9,500 8,500 10,157.50")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), "1")
        self.assertEqual(match.group(2), "3")
        self.assertEqual(match.group(3).strip(), "2005 Château Le Pin")
        self.assertEqual(match.group(6), "8,500")


if __name__ == "__main__":
    unittest.main()
