import unittest

from ingest.fetchers.denzauktionen import DenzauktionenFetcher
from ingest.models import AuctionRef

OVERVIEW_HTML = """
<h3><a href="#">Wein Auktion #297 vom 3. September 2026</a></h3>
<div class="box-content"><p>Some press text.</p></div>
<div class="download-pdf">
    <ul><li><a href="https://denzauktionen.ch/wp-content/uploads/2026/09/297-Resultate-Web-update.pdf" download>Resultate</a></li></ul>
</div>
<h3><a href="#">Wein Auktion #296 vom 4. Juni 2026</a></h3>
<div class="box-content"><p>Other press text.</p></div>
<div class="download-pdf">
    <ul><li><a href="https://denzauktionen.ch/wp-content/uploads/2026/06/296-Resultate-WEB-final.pdf" download>Resultate</a></li></ul>
</div>
"""


class FakeResponse:
    def __init__(self, text=None, content=None):
        self.text = text or ""
        self.content = content if content is not None else self.text.encode()


class FakeSession:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        for key, resp in self.pages.items():
            if key in url:
                return resp
        return FakeResponse("")


class TestDenzauktionen(unittest.TestCase):
    def test_discover_parses_number_date_and_pdf_url(self):
        f = DenzauktionenFetcher()
        session = FakeSession(
            {"vergangene-auktionen": FakeResponse(OVERVIEW_HTML)})
        refs = f.discover(session)
        self.assertEqual([r.auction_id for r in refs], ["297", "296"])
        self.assertEqual(refs[0].date, "2026-09-03")
        self.assertEqual(
            refs[0].url,
            "https://denzauktionen.ch/wp-content/uploads/2026/09/"
            "297-Resultate-Web-update.pdf")

    def test_fetch_downloads_pdf_with_date_encoded_filename(self):
        f = DenzauktionenFetcher()
        ref = AuctionRef("denzauktionen", "297",
                         url="https://example.com/297-Resultate.pdf",
                         date="2026-09-03")
        session = FakeSession(
            {"297-Resultate.pdf": FakeResponse(content=b"%PDF-fake")})
        result = f.fetch(session, ref)
        self.assertEqual(result.content, b"%PDF-fake")
        self.assertEqual(result.filename, "live/297_03092026_Resultate.pdf")


if __name__ == "__main__":
    unittest.main()
