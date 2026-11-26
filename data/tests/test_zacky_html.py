"""load_zacky_html: the raw "Search Results*.html" scrape parser.

Confirmed real (Phase-2 audit, 2026-11-25): 248 such files were first
assumed to be dead search-form/navigation pages based on a single sample.
A full scan found the opposite for most of them -- they are paginated
(20 lots/page) result listings for 5 real, named auctions never present
in the archive's normalized auction-*.json files. The fixture below is
a trimmed two-page capture of one such real auction (page boundary +
currency + unsold/mixed-size edge cases), not invented from scratch.
"""
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import build_db  # noqa: E402

_HEADER = (
    '<option value="9999">Other Auction</option>'
    '<option selected="selected" value="244">'
    'The Bordeaux Flash Auction (January 17-18)</option>'
)

_PAGE1 = f"""<html><body>{_HEADER}
<table id="results">
<tr><td colspan="4">Search Results</td></tr>
<tr class="results-top">
  <td>Lot</td><td>Qty</td><td>Description</td><td>Size</td>
  <td>Price Realized</td>
</tr>
<tr>
  <td><span id="ctl01_lblLotNo">1</span></td>
  <td><span id="ctl01_Label2">6</span></td>
  <td class="description">
    <a href="javascript:x" id="ctl01_hlDesc">Chateau Haut Brion 1994</a>
  </td>
  <td>750ml</td>
  <td align="left"><span id="ctl01_Label6">$1,838</span></td>
</tr>
<tr>
  <td><span id="ctl02_lblLotNo">2</span></td>
  <td><span id="ctl02_Label2">1</span></td>
  <td class="description">
    <a href="javascript:x" id="ctl02_hlDesc">Mixed Case Lot</a>
  </td>
  <td>Mixed</td>
  <td align="left"><span id="ctl02_Label6">Passed</span></td>
</tr>
</table>
</body></html>"""

# Second page: overlaps lot 2 (identical content, confirmed real page-
# boundary behavior) and adds lot 3.
_PAGE2 = f"""<html><body>{_HEADER}
<table id="results">
<tr class="results-top">
  <td>Lot</td><td>Qty</td><td>Description</td><td>Size</td>
  <td>Price Realized</td>
</tr>
<tr>
  <td><span id="ctl01_lblLotNo">2</span></td>
  <td><span id="ctl01_Label2">1</span></td>
  <td class="description">
    <a href="javascript:x" id="ctl01_hlDesc">Mixed Case Lot</a>
  </td>
  <td>Mixed</td>
  <td align="left"><span id="ctl01_Label6">Passed</span></td>
</tr>
<tr>
  <td><span id="ctl02_lblLotNo">3</span></td>
  <td><span id="ctl02_Label2">12</span></td>
  <td class="description">
    <a href="javascript:x" id="ctl02_hlDesc">Chateau Margaux 1993</a>
  </td>
  <td>1.5L</td>
  <td align="left"><span id="ctl02_Label6">$3,200</span></td>
</tr>
</table>
</body></html>"""

_HK_PAGE = f"""<html><body>
<option selected="selected" value="225">
Fine and Rare Wines and Spirits, Hong Kong  (November 19)</option>
<table id="results">
<tr class="results-top">
  <td>Lot</td><td>Qty</td><td>Description</td><td>Size</td>
  <td>Price Realized</td>
</tr>
<tr>
  <td><span id="ctl01_lblLotNo">1</span></td>
  <td><span id="ctl01_Label2">1</span></td>
  <td class="description">
    <a href="javascript:x" id="ctl01_hlDesc">Dom Perignon 2004</a>
  </td>
  <td>750ml</td>
  <td align="left"><span id="ctl01_Label6">HKD17,150</span></td>
</tr>
</table>
</body></html>"""


class LoadZackyHtmlTest(unittest.TestCase):
    def _run(self, files_by_path):
        with tempfile.TemporaryDirectory() as d:
            for rel, content in files_by_path.items():
                path = os.path.join(d, "Zacky", rel)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)
            conn = sqlite3.connect(":memory:")
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_zacky_html(builder, None)
            finally:
                build_db.ARCHIVE = old
            conn.commit()
            return conn

    def test_dedupes_lot_repeated_across_page_boundary(self):
        conn = self._run({
            "2017/17Januar/Search Results.html": _PAGE1,
            "2017/17Januar/Search Results2.html": _PAGE2,
        })
        rows = conn.execute(
            "SELECT lot_no, wine, quantity, bottle_size_dl, realised_price,"
            " sold, mixed_lot, currency FROM lots ORDER BY CAST(lot_no AS "
            "INTEGER)").fetchall()
        self.assertEqual([r[0] for r in rows], ["1", "2", "3"])
        self.assertEqual(rows[0],
                         ("1", "Chateau Haut Brion 1994", 6, 7.5, 1838.0, 1,
                          None, "USD"))
        # "Mixed" size -> no bottle_size_dl, flagged mixed_lot, unsold.
        self.assertEqual(rows[1][3], None)
        self.assertEqual(rows[1][4], None)
        self.assertEqual(rows[1][5], 0)
        self.assertEqual(rows[1][6], 1)
        self.assertEqual(rows[2],
                         ("3", "Chateau Margaux 1993", 12, 15.0, 3200.0, 1,
                          None, "USD"))

    def test_auction_id_uses_html_prefix_to_avoid_collision(self):
        """Confirmed real risk: the site's own internal id "244" already
        exists in the archive's auction-*.json ids for a completely
        different, 2023 auction -- the "html-" prefix avoids merging
        them via add_auction's INSERT-OR-IGNORE fallback."""
        conn = self._run({
            "2017/17Januar/Search Results.html": _PAGE1,
        })
        auction_ids = [r[0] for r in
                      conn.execute("SELECT auction_id FROM auctions")]
        self.assertEqual(auction_ids, ["html-244"])

    def test_year_from_folder_month_from_name_date(self):
        conn = self._run({"2017/17Januar/Search Results.html": _PAGE1})
        row = conn.execute(
            "SELECT auction_date FROM auctions").fetchone()
        self.assertEqual(row[0], "2017-01-01")

    def test_hong_kong_auction_uses_hkd_not_usd(self):
        conn = self._run({"2016/19November/Search Results.html": _HK_PAGE})
        row = conn.execute(
            "SELECT currency FROM auctions").fetchone()
        self.assertEqual(row[0], "HKD")
        lot = conn.execute(
            "SELECT realised_price, currency FROM lots").fetchone()
        self.assertEqual(lot, (17150.0, "HKD"))


if __name__ == "__main__":
    unittest.main()
