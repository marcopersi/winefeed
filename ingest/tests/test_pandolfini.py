import unittest

from ingest.fetchers.pandolfini import PandolfiniFetcher

OVERVIEW_HTML = (
    '<a href="/uk/auction-1448/smartwine-2-0--fleurs-de-vigne.asp">x</a>'
    '<a href="/uk/auction-1376/spring.asp">y</a>'
    '<a href="/uk/auction-1448/dup.asp">z</a>')

LOT_PAGE = (
    '<script type="application/ld+json">'
    '{"@context":"https://schema.org","@graph":['
    '{"@type":"SaleEvent","name":"Smartwine 2.0","startDate":"2026-04-08",'
    '"location":{"@type":"Place","name":"Pandolfini Casa d\'Aste"}},'
    '{"@type":"ItemList","itemListElement":['
    '{"item":{"@type":"Product","name":"Ruinart R de Ruinart","offers":'
    '{"@type":"Offer","price":20,"priceCurrency":"EUR",'
    '"availability":"https://schema.org/SoldOut","url":"https://x/lot"}}},'
    '{"item":{"@type":"Product","name":"Charmes-Chambertin","offers":'
    '{"@type":"Offer","price":300,"priceCurrency":"EUR",'
    '"availability":"https://schema.org/InStock","url":"https://x/lot2"}}}'
    ']}]}</script>')


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


class TestPandolfini(unittest.TestCase):
    def test_discover_dedupes_auction_ids(self):
        f = PandolfiniFetcher()
        refs = f.discover(FakeSession({"fine-and-collectible-wines":
                                      OVERVIEW_HTML}))
        self.assertEqual([r.auction_id for r in refs], ["1448", "1376"])

    def test_fetch_extracts_lots_and_meta(self):
        f = PandolfiniFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("pandolfini", "1448",
                         url="https://www.pandolfini.it/uk/auction-1448/x.asp")
        result = f.fetch(FakeSession({"auction-1448": LOT_PAGE}), ref)
        self.assertEqual(result.data["auction"]["name"], "Smartwine 2.0")
        self.assertEqual(len(result.data["lots"]), 2)
        lot = result.data["lots"][0]
        self.assertEqual(lot["name"], "Ruinart R de Ruinart")
        self.assertEqual(lot["price"], 20)
        self.assertTrue(lot["sold"])


if __name__ == "__main__":
    unittest.main()
