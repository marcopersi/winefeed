import io
import json
import os
import tempfile
import unittest
from unittest import mock

import openpyxl

import orchestrate

RESULTS_HTML = """
<a href="/de/info/results/xlsx/39/weinauktionator_results_39.xlsx">Excel</a>
"""


def _xlsx_bytes():
    buf = io.BytesIO()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Auktionsergebnisse: Sommerauktion 2026"])
    ws.append(["11.07.2026"])
    ws.append([])
    ws.append([])
    ws.append(["Lot", "Anbauregion", "Titel", "Versteigert für", "Weine"])
    ws.append(["09967", "Alsace", "Trimbach, Clos Sainte Hune 2011",
               "---   ", "3 x 0.750 Trimbach"])
    wb.save(buf)
    return buf.getvalue()


class FakeResponse:
    def __init__(self, text="", content=b""):
        self.text = text
        self.content = content

    def raise_for_status(self):
        return None


class FakeSession:
    def get(self, url):
        if "xlsx" in url:
            return FakeResponse(content=_xlsx_bytes())
        return FakeResponse(text=RESULTS_HTML)


class TestOrchestrate(unittest.TestCase):
    def test_runs_and_parses_file_fetcher(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = os.path.join(d, "manifest.json")
            archive = os.path.join(d, "archive")
            session = FakeSession()
            with mock.patch.dict("sys.modules", {}):
                fetched = orchestrate.run_provider(
                    "weinauktionator", session, manifest, archive)
            self.assertEqual(fetched, 1)
            out = os.path.join(archive, "weinauktionator",
                               "weinauktionator_results_39.json")
            self.assertTrue(os.path.exists(out))
            with open(out, encoding="utf-8") as fh:
                parsed = json.load(fh)
            self.assertEqual(len(parsed["lots"]), 1)
            self.assertEqual(parsed["lots"][0]["region"], "Alsace")


if __name__ == "__main__":
    unittest.main()
