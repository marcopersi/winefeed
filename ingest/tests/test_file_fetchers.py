import unittest

from ingest.fetchers.hdh import HdhFetcher
from ingest.fetchers.weinauktionator import WeinauktionatorFetcher

WEIN_RESULTS_HTML = """
<a href="/de/info/results/xlsx/39/weinauktionator_results_39.xlsx">Excel</a>
<a href="/de/info/results/pdf/39/weinauktionator_results_39.pdf">PDF</a>
<a href="/de/info/results/xlsx/38/weinauktionator_results_38.xlsx">Excel</a>
"""

HDH_ARCHIVES_HTML = """
<a href="https://hdhauctions.com/wp-content/uploads/2026/09/2609_AuctionResults.pdf">R</a>
<a href="https://hdhauctions.com/wp-content/uploads/2026/09/2609_catalog.pdf">C</a>
<a href="https://hdhauctions.com/wp-content/uploads/2026/08/2608_AuctionResults.pdf">R</a>
"""


class FakeResponse:
    def __init__(self, text="", content=b""):
        self.text = text
        self.content = content

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, text, content=b"xlsx-bytes"):
        self._text = text
        self._content = content
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return FakeResponse(self._text, self._content)


class TestWeinauktionator(unittest.TestCase):
    def test_discover_unique_numbered_links(self):
        f = WeinauktionatorFetcher()
        refs = f.discover(FakeSession(WEIN_RESULTS_HTML))
        self.assertEqual([r.auction_id for r in refs], ["39", "38"])
        self.assertTrue(refs[0].url.endswith(
            "/de/info/results/xlsx/39/weinauktionator_results_39.xlsx"))

    def test_fetch_returns_bytes(self):
        f = WeinauktionatorFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("weinauktionator", "39",
                         url="https://www.weinauktionator.de/x.xlsx")
        result = f.fetch(FakeSession(""), ref)
        self.assertEqual(result.content, b"xlsx-bytes")
        self.assertEqual(result.filename, "weinauktionator_results_39.xlsx")


class TestHdh(unittest.TestCase):
    def test_discover_results_only(self):
        f = HdhFetcher()
        refs = f.discover(FakeSession(HDH_ARCHIVES_HTML))
        self.assertEqual([r.auction_id for r in refs], ["2609", "2608"])
        self.assertTrue(refs[0].url.endswith("2609_AuctionResults.pdf"))

    def test_fetch_returns_bytes(self):
        f = HdhFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("hdh", "2609",
                         url="https://hdhauctions.com/x.pdf")
        result = f.fetch(FakeSession(""), ref)
        self.assertEqual(result.content, b"xlsx-bytes")
        self.assertEqual(result.filename, "2609_results.pdf")


if __name__ == "__main__":
    unittest.main()
