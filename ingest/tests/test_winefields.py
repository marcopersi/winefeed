import unittest

from ingest.fetchers.winefields import WinefieldsFetcher

OVERVIEW_HTML = (
    '<a href="https://www.winefields.com/auction-highlight/'
    'highlights-wf77-fine-rare-wines-auction/">x</a>')

POST_HTML = (
    '<a href="https://auctions.winefields.com/auctions/1-AO56VE/'
    'wf77-fine-rare-wines-part-i">y</a>')

LOT_PAGE = (
    '"lots":{"result_page":[{"lot_number":1,"title":"Marsannay Rouge",'
    '"status":"sold","sold_price":"200.00","currency_code":"EUR",'
    '"quantity":6,"estimate_low":"160.00","estimate_high":"220.00"}]},'
    '"location_name":"Winefield\'s Amsterdam","percentage_bidding":false,'
    '"default_buyers_premium":null,"currency_code":"EUR"')


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


class TestWinefields(unittest.TestCase):
    def test_discover_follows_highlights(self):
        f = WinefieldsFetcher()
        session = FakeSession({
            "winefields.com/auctions/": OVERVIEW_HTML,
            "auction-highlight": POST_HTML,
        })
        refs = f.discover(session)
        self.assertEqual([r.auction_id for r in refs], ["1-AO56VE"])

    def test_fetch_extracts_lots_and_meta(self):
        f = WinefieldsFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef(
            "winefields", "1-AO56VE",
            url="https://auctions.winefields.com/auctions/1-AO56VE/wf77")
        result = f.fetch(FakeSession({"auctions": LOT_PAGE}), ref)
        self.assertEqual(len(result.data["lots"]), 1)
        lot = result.data["lots"][0]
        self.assertEqual(lot["sold_price"], "200.00")
        self.assertEqual(result.data["auction"]["currency_code"], "EUR")
        self.assertEqual(result.data["auction"]["location_name"],
                         "Winefield's Amsterdam")


if __name__ == "__main__":
    unittest.main()
