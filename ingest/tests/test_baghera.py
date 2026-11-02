import unittest

from ingest.fetchers.baghera import BagheraFetcher
from ingest.models import AuctionRef

ARCHIVE_HTML = """
<a href="https://www.bagherawines.auction/fr/catalogue/voir/175">Kipling#16</a>
<a href="https://www.bagherawines.auction/fr/catalogue/voir/25">Henri Jayer</a>
<a href="https://www.bagherawines.auction/fr/catalogue/voir/176">Wine o'clock #121</a>
"""

DETAIL_HTML_WITH_PDF = """
<title>Henri Jayer, the Heritage</title>
<p>10 mai 2026 14:00</p>
<a href="https://www.bagherawines.auction/assets/uploads/bilan/catalogues/25/Henri_Jayer_The_Heritage-Bagherawines-Sale_Results.pdf">Resultats</a>
<a href="https://www.bagherawines.com/wp-content/uploads/unrelated-magazine.pdf">Magazine</a>
"""

DETAIL_HTML_NO_PDF = """
<title>Wine o'clock Geneve #121</title>
<p>26 mai 2026 14:00</p>
"""


class FakeResponse:
    def __init__(self, text="", content=None, status_code=200):
        self.text = text
        self.content = content if content is not None else text.encode()
        self.status_code = status_code


class FakeSession:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        for key, resp in self.pages.items():
            if key in url:
                return resp
        return FakeResponse(status_code=404)


class TestBaghera(unittest.TestCase):
    def test_discover_lists_every_archive_id(self):
        f = BagheraFetcher()
        session = FakeSession(
            {"catalogue/archive": FakeResponse(ARCHIVE_HTML)})
        refs = f.discover(session)
        self.assertEqual([r.auction_id for r in refs], ["25", "175", "176"])
        self.assertEqual(
            refs[0].url,
            "https://www.bagherawines.auction/fr/catalogue/voir/25")

    def test_fetch_finds_the_pdf_matching_this_id_and_encodes_its_date(self):
        f = BagheraFetcher()
        ref = AuctionRef("baghera", "25",
                         url="https://www.bagherawines.auction/fr/"
                             "catalogue/voir/25")
        session = FakeSession({
            "catalogue/voir/25": FakeResponse(DETAIL_HTML_WITH_PDF),
            "Henri_Jayer_The_Heritage": FakeResponse(content=b"%PDF-fake"),
        })
        result = f.fetch(session, ref)
        self.assertEqual(result.content, b"%PDF-fake")
        self.assertEqual(result.filename, "live/25_20260510_results.pdf")

    def test_fetch_raises_when_no_results_pdf_is_published_yet(self):
        """Confirmed real case: Baghera's recurring "Wine o'clock" sales
        often have no results PDF for months after the sale date --
        raising (instead of archiving nothing) lets orchestrate.py skip
        and retry next run rather than marking it permanently fetched."""
        f = BagheraFetcher()
        ref = AuctionRef("baghera", "176",
                         url="https://www.bagherawines.auction/fr/"
                             "catalogue/voir/176")
        session = FakeSession(
            {"catalogue/voir/176": FakeResponse(DETAIL_HTML_NO_PDF)})
        with self.assertRaises(RuntimeError):
            f.fetch(session, ref)

    def test_fetch_raises_on_http_error(self):
        f = BagheraFetcher()
        ref = AuctionRef("baghera", "999",
                         url="https://www.bagherawines.auction/fr/"
                             "catalogue/voir/999")
        session = FakeSession(
            {"catalogue/voir/999": FakeResponse(status_code=404)})
        with self.assertRaises(RuntimeError):
            f.fetch(session, ref)


if __name__ == "__main__":
    unittest.main()
