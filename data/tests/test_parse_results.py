import json
import os
import sqlite3
import tempfile
import unittest

from parse_results import parse_weinauktionator_xlsx


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


class TestWeinauktionatorLoader(unittest.TestCase):
    def test_loads_parsed_json(self):
        import build_db

        import openpyxl
        with tempfile.TemporaryDirectory() as d:
            xlsx = os.path.join(d, "results_39.xlsx")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.append(["Auktionsergebnisse: Sommerauktion 2026"])
            ws.append(["11.07.2026"])
            ws.append([])
            ws.append([])
            ws.append(["Lot", "Anbauregion", "Titel", "Versteigert für",
                       "Weine"])
            ws.append(["09967", "Alsace", "Trimbach, Clos Sainte Hune 2011",
                       "---   ", "3 x 0.750 Trimbach"])
            ws.append(["09925", "Armagnac", "Laubade, Bas Armagnac 1936",
                       240.0, "1 x 0.700 Laubade"])
            wb.save(xlsx)

            result = parse_weinauktionator_xlsx(xlsx)
            os.makedirs(os.path.join(d, "weinauktionator"), exist_ok=True)
            with open(os.path.join(d, "weinauktionator",
                                   "weinauktionator_results_39.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False)

            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_weinauktionator(builder, None)
            finally:
                build_db.ARCHIVE = old
            conn.commit()

            count = conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
            self.assertEqual(count, 2)
            hammer = conn.execute(
                "SELECT hammer_price FROM lots WHERE lot_no='09925'"
            ).fetchone()[0]
            self.assertEqual(hammer, 240.0)
            conn.close()


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
