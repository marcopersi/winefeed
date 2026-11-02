import json
import unittest

from ingest.fetchers.munichwinecompany import MunichWineCompanyFetcher
from ingest.models import AuctionRef

AUCTIONS_RESPONSE = {
    "success": True,
    "data": {
        "online": {"id": 340, "name": "OA221/ 2026-XV",
                   "date_end": "2026-10-26T21:00:00.000000Z"},
        "upcomingOnline": {"id": 341, "name": "OA222/ 2026-XVI",
                           "date_end": "2026-11-16T21:00:00.000000Z"},
        "live": {"id": 312, "name": "Katalog 2025 IV - A87",
                "desc_en": "Our catalogue auctions have been discontinued"},
        "upcomingLive": None,
    },
}

WINES_RESPONSE = {
    "success": True,
    "items": [
        {"catalogue_nr": 3, "wine": "Pauillac 1er Cru Classe",
         "producer": "Ch. Mouton Rothschild", "year": "2020",
         "area": "Bordeaux", "country": "Frankreich",
         "bottle_count": "1 Flasche", "low": 410, "high": 600,
         "bid": "410.00", "desc": "tasting note"},
        {"catalogue_nr": 4, "wine": "Pauillac 1er Cru Classe",
         "producer": "Ch. Mouton Rothschild", "year": "2019",
         "area": "Bordeaux", "country": "Frankreich",
         "bottle_count": "1 Flasche", "low": 420, "high": 620,
         "bid": None, "desc": "tasting note"},
    ],
}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.requests = []

    def get(self, url):
        self.requests.append(url)
        if url.endswith("/auctions"):
            return FakeResponse(AUCTIONS_RESPONSE)
        if "/wines" in url:
            return FakeResponse(WINES_RESPONSE)
        return FakeResponse({})


class TestMunichWineCompany(unittest.TestCase):
    def test_discover_returns_online_and_live_slots_only(self):
        f = MunichWineCompanyFetcher()
        session = FakeSession()
        refs = f.discover(session)
        self.assertEqual([r.auction_id for r in refs], ["340", "312"])
        self.assertEqual(refs[0].date, "2026-10-26")

    def test_discover_skips_slot_without_id(self):
        f = MunichWineCompanyFetcher()
        session = FakeSession()
        session.get = lambda url: FakeResponse({
            "success": True,
            "data": {"online": None, "live": {"id": None}},
        })
        self.assertEqual(f.discover(session), [])

    def test_fetch_maps_lots_and_marks_unsold(self):
        f = MunichWineCompanyFetcher()
        ref = AuctionRef("munich-wine-company", "340",
                         url="https://cms.munichwinecompany.eu/api/"
                             "auctions/340/wines?all=1")
        result = f.fetch(FakeSession(), ref)
        lots = result.data["lots"]
        self.assertEqual(len(lots), 2)
        self.assertEqual(lots[0]["hammer_price"], "410.00")
        self.assertEqual(lots[0]["region"], "Bordeaux, Frankreich")
        self.assertIsNone(lots[1]["hammer_price"])


if __name__ == "__main__":
    unittest.main()
