import unittest

from ingest.fetchers.idealwine import IdealwineFetcher
from ingest.models import AuctionRef

KNOWN_PRODUCTS = [
    {"product_id": 112168, "vintage": 2023, "wine": "Morgon Côte du Py",
     "estate": "Jean Foillard", "region": "BEAUJOLAIS",
     "appellation": "Morgon", "color": "RED", "classification": None,
     "format": "BOUTEILLE", "code": "2802611"},
    {"product_id": 882, "vintage": 2002, "wine": "La Tâche",
     "estate": None, "region": None, "appellation": None, "color": None,
     "classification": None, "format": None, "code": "2814578"},
]

RATING_DATA = {
    "productVintageRatings": [{"year": 2025, "value": 428184},
                              {"year": 2026, "value": 490620}],
    "lastAdjudications": [
        {"id": 2788532, "soldAt": "2026-09-02T09:12:58+00:00",
         "historicPrice": 490620},
    ],
}
VARIANT_DATA = {
    "variantVariations": [
        {"numberOfBottles": 1, "format": "BOUTEILLE"},
    ],
}


# pylint: disable=too-few-public-methods
class FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self.text = ""

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self):
        self.gets = []

    def get(self, url, **kwargs):  # pylint: disable=unused-argument
        self.gets.append(url)
        if "morgon-cote-du-py" in url:
            return FakeResponse(
                {"pageProps": {
                    "__N_REDIRECT":
                        "/de/kaufen-ein-wein/2802611-1-Magnum-Morgon-2023-Rot",
                }})
        return FakeResponse({"pageProps": {"dehydratedState": {"queries": [
            {"queryKey": ["pdp-displayed-vintage-rating", "112168-2023"],
             "state": {"data": RATING_DATA}},
            {"queryKey": ["syliusApiShopProductVariantGet", "2802611"],
             "state": {"data": VARIANT_DATA}},
        ]}}})


class TestIdealwine(unittest.TestCase):
    def test_discover_known_products_builds_refs_from_snapshot(self):
        f = IdealwineFetcher(build_id="b1")
        refs = f.discover_known_products(FakeSession(), KNOWN_PRODUCTS)
        self.assertEqual(len(refs), 2)
        self.assertEqual(refs[0].auction_id, "112168-2023")
        self.assertEqual(refs[0].date, "2023")
        self.assertEqual(
            refs[0].url,
            "https://www.idealwine.com/_next/data/b1/de/"
            "kaufen-ein-wein/2802611-morgon-cote-du-py.json")
        self.assertEqual(refs[0].meta["estate"], "Jean Foillard")
        self.assertEqual(refs[0].meta["region"], "BEAUJOLAIS")
        self.assertEqual(refs[0].meta["appellation"], "Morgon")
        self.assertEqual(refs[0].meta["product_variant_id"], "2802611")

    def test_discover_known_products_skips_entries_without_a_code(self):
        f = IdealwineFetcher(build_id="b1")
        refs = f.discover_known_products(FakeSession(), [
            {"product_id": 1, "vintage": 2020, "wine": "No Code",
             "code": None},
        ])
        self.assertEqual(refs, [])

    def test_fetch_follows_redirect_and_reads_dehydrated_cote(self):
        f = IdealwineFetcher(build_id="b1")
        session = FakeSession()
        ref = AuctionRef(
            provider="idealwine", auction_id="112168-2023",
            url="https://www.idealwine.com/_next/data/b1/de/"
                "kaufen-ein-wein/2802611-morgon-cote-du-py.json",
            title="Morgon Côte du Py", date="2023",
            meta={"product_id": 112168, "vintage": 2023,
                  "wine": "Morgon Côte du Py", "estate": "Jean Foillard",
                  "region": "BEAUJOLAIS", "appellation": "Morgon",
                  "color": "RED", "format": "BOUTEILLE",
                  "product_variant_id": 2802611})
        result = f.fetch(session, ref)
        self.assertEqual(
            result.data["lastAdjudications"][0]["historicPrice"], 490620)
        self.assertEqual(result.data["productVintageRatings"],
                         RATING_DATA["productVintageRatings"])
        self.assertEqual(result.data["meta"]["estate"], "Jean Foillard")
        self.assertEqual(result.data["meta"]["bottles"], 1)
        self.assertEqual(len(session.gets), 2)

    def test_fetch_keeps_snapshot_format_when_no_variant_query_matches(self):
        """Review finding (2026-11-25): discover_known_products() seeds
        meta["format"] from the snapshot's own last-known adjudication
        format as a fallback. If the live page no longer embeds a
        matching syliusApiShopProductVariantGet query for this exact
        variant id (e.g. a long-delisted lot), fetch() must keep that
        fallback instead of silently losing it to None."""
        f = IdealwineFetcher(build_id="b1")

        class NoVariantSession(FakeSession):
            def get(self, url, **kwargs):
                return FakeResponse({"pageProps": {"dehydratedState": {
                    "queries": [
                        {"queryKey": ["pdp-displayed-vintage-rating",
                                      "112168-2023"],
                         "state": {"data": RATING_DATA}},
                        # No syliusApiShopProductVariantGet query at all.
                    ]}}})

        ref = AuctionRef(
            provider="idealwine", auction_id="112168-2023",
            url="https://www.idealwine.com/_next/data/b1/de/"
                "kaufen-ein-wein/other-slug.json",
            title="Morgon Côte du Py", date="2023",
            meta={"product_id": 112168, "vintage": 2023,
                  "format": "BOUTEILLE", "product_variant_id": 2802611})
        result = f.fetch(NoVariantSession(), ref)
        self.assertEqual(result.data["meta"]["format"], "BOUTEILLE")
        self.assertIsNone(result.data["meta"]["bottles"])

    def test_picks_the_matching_query_when_two_share_a_prefix(self):
        """Confirmed real gap: matching queryKey[0] alone would return
        whichever same-prefixed query came first, regardless of which
        product/variant it's actually for -- a page that ever embeds a
        second rating/variant query (e.g. a prefetched related-wine
        widget) must not have its data silently misattributed here."""
        f = IdealwineFetcher(build_id="b1")

        class TwoQuerySession(FakeSession):
            def get(self, url, **kwargs):
                return FakeResponse({"pageProps": {"dehydratedState": {
                    "queries": [
                        {"queryKey": ["pdp-displayed-vintage-rating",
                                      "999-1999"],
                         "state": {"data": {"productVintageRatings": [],
                                            "lastAdjudications": [
                                                {"id": 1, "soldAt": "x",
                                                 "historicPrice": 1}]}}},
                        {"queryKey": ["pdp-displayed-vintage-rating",
                                      "112168-2023"],
                         "state": {"data": RATING_DATA}},
                        {"queryKey": ["syliusApiShopProductVariantGet",
                                      "999999"],
                         "state": {"data": {"variantVariations": [
                             {"numberOfBottles": 6, "format": "MAGNUM"}]}}},
                        {"queryKey": ["syliusApiShopProductVariantGet",
                                      "2802611"],
                         "state": {"data": VARIANT_DATA}},
                    ]}}})

        session = TwoQuerySession()
        ref = AuctionRef(
            provider="idealwine", auction_id="112168-2023",
            url="https://www.idealwine.com/_next/data/b1/de/"
                "kaufen-ein-wein/other-slug.json",
            title="Morgon Côte du Py", date="2023",
            meta={"product_id": 112168, "vintage": 2023,
                  "product_variant_id": 2802611})
        result = f.fetch(session, ref)
        self.assertEqual(
            result.data["lastAdjudications"][0]["historicPrice"], 490620)
        self.assertEqual(result.data["meta"]["bottles"], 1)
        self.assertEqual(result.data["meta"]["format"], "BOUTEILLE")


if __name__ == "__main__":
    unittest.main()
