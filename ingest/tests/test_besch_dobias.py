import unittest

from ingest.fetchers.beschcannes import BeschCannesFetcher
from ingest.fetchers.dobiaschofsky import DobiaschofskyFetcher

BESCH_LIST = ('<a href="/auctions/408-grands-vins-alcools">x</a>'
              '<a href="/auctions/407-grands-vins-alcools">y</a>'
              '<a href="/auctions/408-dup">z</a>')

BESCH_PAGE = (
    '<div class="shop-item"><div class="thumbnail">'
    '<a href="/en-lots/88069" class="shop-item-image"><img alt="Lot : 401">'
    '</a><span class="result">Sold 2 650 €</span></div>'
    '<div class="shop-item-summary"><h2 class="title-product">Lot : n° 401</h2>'
    '<div class="shop-item-price">1 000 € / 1 500 €</div></div></div>')

DOBIAS_PAGE = (
    '<form action="/d346-A129-12550-x.html">'
    '<h3>DOMAINE DE LA ROMANEE</h3>'
    '<span style="color:#004e6c">Zuschlag: CHF 10\'000</span>'
    '<span style="font-size:11px">A-129: November 2019</span></form>')


class FakeResponse:
    def __init__(self, text):
        self.text = text
        self.content = b""

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, pages):
        self._pages = pages

    def get(self, url):
        for key, text in self._pages.items():
            if key in url:
                return FakeResponse(text)
        return FakeResponse("")


class TestBeschCannes(unittest.TestCase):
    def test_discover_dedupes(self):
        f = BeschCannesFetcher()
        refs = f.discover(FakeSession({"past-auctions": BESCH_LIST}))
        self.assertEqual([r.auction_id for r in refs], ["408", "407"])

    def test_fetch_extracts_lots(self):
        f = BeschCannesFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("besch-cannes", "408", url="https://x/auctions/408")
        result = f.fetch(FakeSession({"auctions/408": BESCH_PAGE}), ref)
        lot = result.data["lots"][0]
        self.assertEqual(lot["hammer"], "Sold 2 650 €")
        self.assertEqual(lot["url"], "/en-lots/88069")


class TestDobiaschofsky(unittest.TestCase):
    def test_fetch_extracts_lots(self):
        f = DobiaschofskyFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("dobiaschofsky", "wein",
                         url="https://www.dobiaschofsky.com/d346.html")
        result = f.fetch(FakeSession({"d346.html": DOBIAS_PAGE}), ref)
        lot = result.data["lots"][0]
        self.assertEqual(lot["name"], "DOMAINE DE LA ROMANEE")
        self.assertEqual(lot["hammer"], "Zuschlag: CHF 10'000")
        self.assertEqual(lot["auction"], "A-129: November 2019")


if __name__ == "__main__":
    unittest.main()
