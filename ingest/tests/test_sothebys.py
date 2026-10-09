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
    '"Auction:QXVjdGlvbl9kMTliYmI4ZS03MWM0LTQyYjktYWJhNS0zNjZkMzExODA2YTk=":'
    '{"auctionId":"d19bbb8e-71c4-42b9-aba5-366d311806a9"}}}}}'
    '</script>')

GRAPHQL_RESPONSE = {
    "data": {"auction": {"lotCardsConnection": {
        "lots": [{"title": "The Macallan 42.6",
                  "lotNumber": {"lotDisplayNumber": "1"},
                  "bidState": {"bidAsk": "140000"},
                  "estimateV2": {"lowEstimate": {"amount": "60000"},
                                 "highEstimate": {"amount": "100000"}},
                  "auction": {"currency": "GBP",
                              "locationV2": {"name": "London"},
                              "sapSaleNumber": "L26722",
                              "state": "Closed"}}],
        "totalCount": 1,
    }}}
}


class FakeResponse:
    def __init__(self, text=None, payload=None):
        self.text = text or ""
        self._payload = payload
        self.content = b""

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, pages, graphql=None):
        self._pages = pages
        self._graphql = graphql or {}
        self.cookies = _CookieJar()

    def get(self, url):
        for key, text in self._pages.items():
            if key in url:
                return FakeResponse(text)
        return FakeResponse("")

    def post(self, *args, **kwargs):  # pylint: disable=unused-argument
        return FakeResponse(payload=self._graphql)


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

    def test_fetch_extracts_lots_with_hammer(self):
        f = SothebysFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("sothebys", "finest-whiskies-l26722",
                         url="https://x/auction/x")
        session = FakeSession({"auction/x": NEXT_DATA}, GRAPHQL_RESPONSE)
        result = f.fetch(session, ref)
        lot = result.data["lots"][0]
        self.assertEqual(lot["title"], "The Macallan 42.6")
        self.assertEqual(lot["hammer"], "140000")
        self.assertEqual(lot["estimate_low"], "60000")
        self.assertEqual(lot["currency"], "GBP")
        self.assertEqual(lot["location"], "London")


if __name__ == "__main__":
    unittest.main()
