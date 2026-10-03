import unittest

from ingest.fetchers.idealwine import IdealwineFetcher
from ingest.models import AuctionRef

ALGOLIA_PAGE = {
    "hits": [
        {"id": 2802611, "name": "Morgon Côte du Py", "vintage": 2023,
         "product": 112168},
        {"id": 2814578, "name": "La Tâche", "vintage": 2002, "product": 882},
    ],
}

COTE = {
    "productVintageCode": "112168-2023",
    "lastAdjudications": [
        {"soldAt": "2026-09-02T09:12:58+00:00", "price": 2500},
    ],
}


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = ""

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.gets = []
        self.posts = []

    def get(self, url, headers=None):
        self.gets.append(url)
        if "morgon-cote-du-py" in url:
            return FakeResponse(
                {"pageProps": {
                    "__N_REDIRECT":
                        "/de/kaufen-ein-wein/2802611-1-Magnum-Morgon-2023-Rot",
                }})
        return FakeResponse({"pageProps": {"productVintageRatings": COTE}})

    def post(self, url, headers=None, json=None):
        self.posts.append(url)
        return FakeResponse(ALGOLIA_PAGE)


class TestIdealwine(unittest.TestCase):
    def test_discover_builds_refs_from_algolia(self):
        f = IdealwineFetcher(build_id="b1")
        refs = f.discover(FakeSession())
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0].auction_id, "112168-2023")
        self.assertEqual(refs[0].date, "2023")
        self.assertTrue(refs[0].url.startswith(
            "https://www.idealwine.com/_next/data/b1/de/"
            "kaufen-ein-wein/2802611-morgon-cote-du-py.json"))

    def test_fetch_follows_redirect_to_cote(self):
        f = IdealwineFetcher(build_id="b1")
        session = FakeSession()
        ref = AuctionRef(
            provider="idealwine", auction_id="2802611",
            url="https://www.idealwine.com/_next/data/b1/de/"
                "kaufen-ein-wein/2802611-morgon-cote-du-py.json",
            title="Morgon Côte du Py", date="2023")
        result = f.fetch(session, ref)
        self.assertEqual(result.data["productVintageCode"], "112168-2023")
        self.assertEqual(result.data["lastAdjudications"][0]["price"], 2500)
        self.assertEqual(len(session.gets), 2)


if __name__ == "__main__":
    unittest.main()
