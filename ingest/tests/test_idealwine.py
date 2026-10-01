import unittest

from ingest.fetchers.idealwine import IdealwineFetcher

REGION_PAGE = {
    "hydra:member": [
        {"productId": 100, "year": 2020, "wineName": "Château Canon"},
        {"productId": 100, "year": 2019, "wineName": "Château Canon"},
    ],
    "hydra:totalItems": 2,
}

RATING_INFO = {"productVintageCode": "100-2020", "lastAdjudications": []}


class FakeSession:
    def __init__(self):
        self.requests = []

    def get(self, url, headers=None):
        self.requests.append(url)
        if "by-region" in url:
            return FakeResponse(REGION_PAGE)
        return FakeResponse(RATING_INFO)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class TestIdealwine(unittest.TestCase):
    def test_discover_all_regions(self):
        f = IdealwineFetcher()
        refs = f.discover(FakeSession())
        # 3 regions x 2 members = 6 refs
        self.assertEqual(len(refs), 6)
        self.assertEqual(refs[0].auction_id, "100-2020")

    def test_fetch(self):
        f = IdealwineFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef(provider="idealwine", auction_id="100-2020",
                         url="https://www.idealwine.com/api/v2/shop/product-vintage-rating-info/100-2020")
        result = f.fetch(FakeSession(), ref)
        self.assertEqual(result.data["productVintageCode"], "100-2020")


if __name__ == "__main__":
    unittest.main()
