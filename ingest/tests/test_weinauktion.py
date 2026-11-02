import unittest

from ingest.fetchers.weinauktion import WeinauktionFetcher
from ingest.models import AuctionRef

AUCTIONS = [
    {
        "id": 617,
        "title": "eAuktion 116",
        "startDate": "2026-01-31T00:00:00+00:00",
        "currency": "CHF",
        "catalogs": [{"id": 627, "title": "eAuktion 116"}],
    },
]

LOTS_PAGE = {
    "@related": {
        "auctions": [{"id": 617, "title": "eAuktion 116",
                      "currency": "CHF"}],
        "catalogs": [{"id": 627}],
    },
    "$page": 1,
    "$totalPages": 2,
    "$totalCount": 2,
    "items": [{"id": 1, "number": "1", "hammerPrice": 34.0,
               "basePrice": 20.0, "upperBasePrice": 40.0,
               "state": "sold", "shortDescription": "Barolo 2015"}],
}


class FakeSession:
    def __init__(self, pages):
        self.pages = pages  # list of lots pages
        self.requests = []

    def get(self, url, headers=None):
        self.requests.append(url)
        if "/api/auctions" in url:
            return FakeResponse(AUCTIONS)
        return FakeResponse(self.pages.pop(0))


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class TestWeinauktion(unittest.TestCase):
    def test_sends_current_api_version(self):
        """Confirmed real case: the live API moved from 1.14 to 2.3 and
        started rejecting 1.14 with a bare 400 -- broke steinfels AND
        weinboerse in CI (run 41257477575, 2026-11-01) until this was
        caught and bumped."""
        f = WeinauktionFetcher("steinfels", "https://auktionen.steinfelsweine.ch")
        self.assertEqual(f._headers()["x-api-version"], "2.3")

    def test_discover(self):
        f = WeinauktionFetcher("steinfels", "https://auktionen.steinfelsweine.ch")
        refs = f.discover(FakeSession([]))
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].auction_id, "627")
        self.assertEqual(refs[0].title, "eAuktion 116")

    def test_fetch_paginates(self):
        f = WeinauktionFetcher("steinfels", "https://auktionen.steinfelsweine.ch")
        session = FakeSession([LOTS_PAGE, LOTS_PAGE])
        result = f.fetch(session, AuctionRef("steinfels", "627"))
        self.assertEqual(len(result.data["lots"]), 2)  # 2 pages x 1 item
        self.assertEqual(result.data["auction"]["id"], "627")
        self.assertEqual(result.data["auction"]["name"], "eAuktion 116")
        lot = result.data["lots"][0]
        self.assertEqual(lot["lot_no"], "1")
        self.assertEqual(lot["hammer_price"], 34.0)
        self.assertEqual(lot["estimate_low"], 20.0)
        self.assertEqual(lot["vintage"], "2015")
        self.assertEqual(lot["sold"], 1)
        self.assertIsNone(lot["description"])  # no raw description on this fixture
        # pagination requested page 1 and 2
        lot_urls = [u for u in session.requests if "/api/lots" in u]
        self.assertIn("$page=1", lot_urls[0])
        self.assertIn("$page=2", lot_urls[1])


    def test_map_lot_preserves_raw_description(self):
        """The flattened 'wine' text loses structure a fuller re-parse
        could recover later -- the raw HTML must survive this layer."""
        lot = WeinauktionFetcher._map_lot(
            {"number": "1", "description": "Clos de la Roche gr.c., OHK"
                                            "<br />Jahrgang: 2011"},
            "CHF")
        self.assertEqual(lot["description"],
                         "Clos de la Roche gr.c., OHK<br />Jahrgang: 2011")


if __name__ == "__main__":
    unittest.main()
