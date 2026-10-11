import io
import json
import os
import sqlite3
import tempfile
import unittest
from unittest import mock

import openpyxl

import build_db
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
    def test_archive_dir_and_filename_mapping(self):
        from ingest.models import AuctionRef
        self.assertEqual(orchestrate._archive_dir("hdh"), "HDH")
        self.assertEqual(orchestrate._archive_dir("sothebys"), "Sothebys")
        self.assertEqual(orchestrate._archive_dir("koppe"), "Koppe")
        self.assertEqual(orchestrate._archive_dir("weinauktionator"),
                         "weinauktionator")
        self.assertEqual(
            orchestrate._json_filename(
                "besch-cannes", AuctionRef("besch-cannes", "408")),
            "auction-408.json")
        self.assertEqual(
            orchestrate._json_filename(
                "dobiaschofsky", AuctionRef("dobiaschofsky", "wein")),
            "auktion-wein.json")
        self.assertEqual(
            orchestrate._json_filename(
                "langtons", AuctionRef("langtons", "8212")),
            "8212.json")

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

    def test_is_valid_guard(self):
        from ingest.models import FetchResult
        empty = FetchResult("sothebys", "x", data={"auction": {}, "lots": []})
        self.assertFalse(orchestrate._is_valid(empty))
        json_lot = FetchResult("langtons", "x",
                               data={"auction": {"id": "1"}, "lots": []})
        self.assertTrue(orchestrate._is_valid(json_lot))
        binary = FetchResult("weinauktionator", "x", content=b"data")
        self.assertTrue(orchestrate._is_valid(binary))

    def test_runs_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = os.path.join(d, "manifest.json")
            archive = os.path.join(d, "archive")
            session = FakeSession()
            with mock.patch.dict("sys.modules", {}):
                first = orchestrate.run_provider(
                    "weinauktionator", session, manifest, archive)
                second = orchestrate.run_provider(
                    "weinauktionator", session, manifest, archive)
            self.assertEqual(first, 1)
            self.assertEqual(second, 0)
            files = os.listdir(os.path.join(archive, "weinauktionator"))
            self.assertEqual(files, ["weinauktionator_results_39.json"])

    def test_json_fetcher_end_to_end(self):
        closed = ('<a href="Auction-ShowDetails?id=8212&amp;name=F27UR014'
                  '&amp;title=04%20SUN%3a%20Unreserved">')
        lot = (
            '<tbody class="auction-closed-row-tbody">'
            '<tr class="auction-closed-sm-data">'
            '<td class="column-header" data-label="Lot #"><span>1</span></td>'
            '<td class="column-header hidden-sm-down">'
            '<p class="wine-name">Penfolds Grange</p>'
            '<p class="wine-description">South Australia</p></td>'
            '<td class="column-header" data-label="Vintage">'
            '<span>2019</span></td>'
            '<td class="column-header" data-label="Quantity">'
            '<span>1</span></td>'
            '<td class="column-header" data-label="Winning bid per item">'
            '<span>$850.00</span></td></tr></tbody>')

        class LangtonsSession:
            def get(self, url):
                if "ClosedAuction" in url:
                    return FakeResponse(text=closed)
                return FakeResponse(text=lot)

        with tempfile.TemporaryDirectory() as d:
            manifest = os.path.join(d, "manifest.json")
            archive = os.path.join(d, "archive")
            session = LangtonsSession()
            with mock.patch.dict("sys.modules", {}):
                fetched = orchestrate.run_provider(
                    "langtons", session, manifest, archive)
            self.assertEqual(fetched, 1)
            out = os.path.join(archive, "Langtons", "8212.json")
            self.assertTrue(os.path.exists(out))
            old = build_db.ARCHIVE
            build_db.ARCHIVE = archive
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            try:
                build_db.load_langtons(builder, None)
            finally:
                build_db.ARCHIVE = old
            conn.commit()
            count = conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
            hammer = conn.execute(
                "SELECT hammer_price FROM lots WHERE wine='Penfolds Grange'"
            ).fetchone()[0]
            conn.close()
            self.assertEqual(count, 1)
            self.assertEqual(hammer, 850.0)


if __name__ == "__main__":
    unittest.main()
