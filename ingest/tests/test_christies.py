import unittest

from ingest.fetchers.christies import ChristiesFetcher

RESULTS_HTML = (
    '\\"department\\":\\"Wine \\u0026 Spirits\\",\\"saleNumber\\":\\"24465\\",'
    '\\"saleId\\":\\"31122\\"'
    '\\"department\\":\\"Watches \\u0026 Wristwatches\\",\\"saleNumber\\":'
    '\\"24477\\",\\"saleId\\":\\"31133\\"'
    '\\"department\\":\\"Wine \\u0026 Spirits\\",\\"saleNumber\\":\\"24465\\",'
    '\\"saleId\\":\\"31122\\"')

AUCTION_HTML = (
    '{"sale_id":"31122","sale_location":"HongKong",'
    '"sale_number":"24465","sale_room_code":"HGK",'
    '"title":"The Cellar of the Hon. Henry Tang",'
    '"auction_status":{"start_date":"2026-10-10T00:00Z"}}')

LOT = {
    "lot_id_txt": "1",
    "title_primary_txt": "Château Lafite Rothschild 1953",
    "title_secondary_txt": "1 Magnum (150cl) per lot",
    "estimate_low": 70000.0,
    "estimate_high": 100000.0,
    "price_realised": 118750.0,
    "lot_withdrawn": False,
    "price_realised_txt": "HKD 118,750",
    "url": "https://www.christies.com/en/lot/lot-6604342",
}


class FakeResponse:
    def __init__(self, text="", payload=None):
        self.text = text
        self._payload = payload
        self.content = b""

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, results="", auction="", lotsearch_pages=None):
        self._results = results
        self._auction = auction
        self._pages = lotsearch_pages or []

    def get(self, url, params=None, headers=None):  # pylint: disable=unused-argument
        if "/en/results" in url:
            return FakeResponse(text=self._results)
        if "lotsearch" in url:
            if self._pages:
                return FakeResponse(payload=self._pages.pop(0))
            return FakeResponse(payload={"lots": [], "total_hits_filtered": 0})
        return FakeResponse(text=self._auction)


class TestChristies(unittest.TestCase):
    def test_discover_filters_wine_auctions(self):
        f = ChristiesFetcher()
        refs = f.discover(FakeSession(results=RESULTS_HTML))
        self.assertEqual([r.auction_id for r in refs], ["31122"])

    def test_fetch_maps_lots(self):
        f = ChristiesFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("christies", "31122",
                         url="https://www.christies.com/en/auction/auction-31122")
        session = FakeSession(
            auction=AUCTION_HTML,
            lotsearch_pages=[{"lots": [LOT], "total_hits_filtered": 1}])
        result = f.fetch(session, ref)
        auction = result.data["auction"]
        self.assertEqual(auction["event_id"], "31122")
        self.assertEqual(auction["title"], "The Cellar of the Hon. Henry Tang")
        self.assertEqual(auction["location"], "HongKong")
        self.assertEqual(auction["year"], 2026)
        lot = result.data["lots"][0]
        self.assertEqual(lot["lot_number"], "1")
        self.assertEqual(lot["title"], "Château Lafite Rothschild 1953")
        self.assertEqual(lot["price_realised"], 118750.0)
        self.assertEqual(lot["currency"], "HKD")
        self.assertEqual(lot["description"], "1 Magnum (150cl) per lot")

    def test_fetch_paginates_all_lots(self):
        f = ChristiesFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("christies", "31122",
                         url="https://www.christies.com/en/auction/auction-31122")
        page1 = {"lots": [LOT], "total_hits_filtered": 2}
        lot2 = dict(LOT, lot_id_txt="2",
                    title_primary_txt="Château Latour 1982")
        page2 = {"lots": [lot2], "total_hits_filtered": 2}
        session = FakeSession(
            auction=AUCTION_HTML, lotsearch_pages=[page1, page2])
        result = f.fetch(session, ref)
        self.assertEqual(len(result.data["lots"]), 2)
        self.assertEqual(result.data["lots"][1]["title"], "Château Latour 1982")

    def test_fetch_fails_loud_when_total_missing(self):
        f = ChristiesFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("christies", "31122",
                         url="https://www.christies.com/en/auction/auction-31122")
        session = FakeSession(
            auction=AUCTION_HTML, lotsearch_pages=[{"lots": [LOT]}])
        with self.assertRaises(RuntimeError):
            f.fetch(session, ref)

    def test_fetch_raises_on_reconciliation_mismatch(self):
        f = ChristiesFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("christies", "31122",
                         url="https://www.christies.com/en/auction/auction-31122")
        session = FakeSession(
            auction=AUCTION_HTML,
            lotsearch_pages=[{"lots": [LOT], "total_hits_filtered": 5}])
        with self.assertRaises(RuntimeError):
            f.fetch(session, ref)

    def test_is_wine_title_ground_truth(self):
        from ingest.fetchers.christies import _is_wine_title
        wine = ["Fine and Rare Wines",
                "A Gentleman's Palate: A Journey Through Three Centuries "
                "of Wine",
                "Fine Wine", "Vins de Bourgogne",
                "Fine and Rare Wines and Vintage Cigars"]
        for title in wine:
            self.assertTrue(_is_wine_title(title), title)
        not_wine = ["ART AFRICAIN, OCEANIEN ET PRECOLOMBIEN",
                    "Fine Chinese Ceramics and Works of Art",
                    "Furniture and Decorative Objects", "Jewellery",
                    "The House Sale", "Vintage Film Posters",
                    "Shipping and Vintage Posters",
                    "The Spirit of India: Modern South Asian Art",
                    "A Feast for the Palate: Fine Dining and Cookery",
                    "Burgundy Velvet and Silver",
                    "The Cellar Door: A Story of Collecting",
                    "Signature Cellars"]
        for title in not_wine:
            self.assertFalse(_is_wine_title(title), title)

    def test_validate_backfill_meta(self):
        from ingest.fetchers.christies import _validate_backfill_meta
        ok = {"sale_id": "18467", "sale_number": "5057", "saleroomcode": "PAR",
              "year": 2003, "month": 6}
        _validate_backfill_meta(ok)
        with self.assertRaises(RuntimeError):
            _validate_backfill_meta({"sale_id": "18467"})

    def test_discover_backfill_filters_wine(self):
        f = ChristiesFetcher()
        index = ('<sitemapindex><sitemap><loc>'
                 'https://www.christies.com/SiteMapPastSales1.xml'
                 '</loc></sitemap></sitemapindex>')
        sales = ('<urlset>'
                 '<url><loc>https://www.christies.com/auction/'
                 'auction-5057-par/browse-lots</loc></url>'
                 '<url><loc>https://www.christies.com/auction/'
                 'auction-7187-lon/browse-lots</loc></url>'
                 '</urlset>')
        art = ('{"sale_id":"18467","sale_number":"5057",'
               '"sale_room_code":"PAR","title":"ART AFRICAIN",'
               '"auction_status":{"start_date":"2003-06-12T00:00Z"}}')
        wine = ('{"sale_id":"12345","sale_number":"7187",'
                '"sale_room_code":"LON","title":"Fine and Rare Wines",'
                '"auction_status":{"start_date":"2020-06-01T00:00Z"}}')

        class BackfillSession:
            def get(self, url):
                if "LotFinder_Sitemap1" in url:
                    return FakeResponse(text=index)
                if "SiteMapPastSales" in url:
                    return FakeResponse(text=sales)
                if "auction-5057" in url:
                    return FakeResponse(text=art)
                return FakeResponse(text=wine)

        refs = f.discover_backfill(BackfillSession())
        self.assertEqual([r.auction_id for r in refs], ["12345"])
        self.assertEqual(refs[0].title, "Fine and Rare Wines")


if __name__ == "__main__":
    unittest.main()
