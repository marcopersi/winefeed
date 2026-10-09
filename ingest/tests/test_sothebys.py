import unittest
from unittest import mock

from ingest.fetchers.sothebys import SothebysFetcher

RESULTS_HTML = (
    '<a href="/en/buy/auction/2026/finest-whiskies-l26722">x</a>'
    '<a href="/en/buy/auction/2026/fine-wines-n123">y</a>'
    '<a href="/en/buy/auction/2026/finest-whiskies-l26722">dup</a>')

NEXT_DATA = (
    '<script id="__NEXT_DATA__" type="application/json">'
    '{"props":{"pageProps":{"apolloCache":{'
    '"LotCard:bG90":{"title":"The Macallan 42.6","lotNumber":'
    '{"lotDisplayNumber":"1"},"auction":{"currency":"GBP",'
    '"locationV2":{"name":"London"},"sapSaleNumber":"L26722",'
    '"state":"Closed"},"estimateV2":"100 - 200"}}}}}'
    '</script>')


class FakeResponse:
    def __init__(self, text):
        self.text = text
        self.content = b""

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, pages):
        self._pages = pages
        self.cookies = _CookieJar()

    def get(self, url):
        for key, text in self._pages.items():
            if key in url:
                return FakeResponse(text)
        return FakeResponse("")


class _CookieJar:
    def __init__(self):
        self._store = {}

    def set(self, name, value, **kwargs):  # pylint: disable=unused-argument
        self._store[name] = value

    def get(self, name):
        return self._store.get(name)


class TestSothebys(unittest.TestCase):
    def test_auth_sets_globid_cookie(self):
        f = SothebysFetcher()
        session = FakeSession({})
        env = {"SOTHEBYS_USER": "u", "SOTHEBYS_PWD": "p"}
        with mock.patch("ingest.fetchers.sothebys.sothebys_login",
                        return_value="jwt-token"):
            self.assertTrue(f.auth(session, env))
        self.assertEqual(session.cookies.get("globid"), "jwt-token")

    def test_discover_dedupes_slugs(self):
        f = SothebysFetcher()
        refs = f.discover(FakeSession({"en/results": RESULTS_HTML}))
        self.assertEqual([r.auction_id for r in refs],
                         ["finest-whiskies-l26722", "fine-wines-n123"])

    def test_fetch_extracts_lot_cards(self):
        f = SothebysFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("sothebys", "finest-whiskies-l26722",
                         url="https://x/auction/x")
        result = f.fetch(FakeSession({"auction": NEXT_DATA}), ref)
        lot = result.data["lots"][0]
        self.assertEqual(lot["title"], "The Macallan 42.6")
        self.assertEqual(lot["lot_no"], "1")
        self.assertEqual(lot["currency"], "GBP")
        self.assertEqual(lot["location"], "London")


if __name__ == "__main__":
    unittest.main()
