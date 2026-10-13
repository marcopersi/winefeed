import unittest
from unittest.mock import patch

from ingest.fetchers.christies import (
    PERMANENT_SKIP, ChristiesFetcher, MalformedResponse, MetaInvalid,
    ReconciliationMismatch, _classify_title, _is_wine_title,
    _validate_backfill_meta,
)

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
    def __init__(self, text="", payload=None, status_code=200):
        self.text = text
        self._payload = payload
        self.content = b""
        self.status_code = status_code

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, results="", auction="", lotsearch_pages=None,
                 url_responses=None):
        self._results = results
        self._auction = auction
        self._pages = lotsearch_pages or []
        self._url_responses = url_responses or {}
        self.request_log = []

    def get(self, url, params=None, headers=None):  # pylint: disable=unused-argument
        self.request_log.append(url)
        if url in self._url_responses:
            return self._url_responses[url]
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

    def test_fetch_raises_malformed_when_total_missing(self):
        f = ChristiesFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("christies", "31122",
                         url="https://www.christies.com/en/auction/auction-31122")
        session = FakeSession(
            auction=AUCTION_HTML, lotsearch_pages=[{"lots": [LOT]}])
        with self.assertRaises(MalformedResponse):
            f.fetch(session, ref)

    def test_fetch_raises_reconciliation_mismatch(self):
        f = ChristiesFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("christies", "31122",
                         url="https://www.christies.com/en/auction/auction-31122")
        session = FakeSession(
            auction=AUCTION_HTML,
            lotsearch_pages=[{"lots": [LOT], "total_hits_filtered": 5}])
        with self.assertRaises(ReconciliationMismatch):
            f.fetch(session, ref)

    def test_classify_title_three_way(self):
        self.assertEqual(_classify_title("Fine and Rare Wines"), "WINE")
        self.assertEqual(_classify_title("Vins de Bourgogne"), "WINE")
        self.assertEqual(_classify_title("Fine Whisky"), "WINE")
        self.assertEqual(_classify_title("Rare Spirits"), "AMBIGUOUS")
        self.assertEqual(_classify_title("Signature Cellars"), "AMBIGUOUS")
        self.assertEqual(_classify_title("Burgundy Velvet and Silver"),
                         "AMBIGUOUS")
        self.assertEqual(_classify_title("The Cellar Door: Collecting"),
                         "AMBIGUOUS")
        self.assertEqual(_classify_title("Fine Cognac and Armagnac"),
                         "AMBIGUOUS")
        self.assertEqual(_classify_title("Jewellery"), "NOT_WINE")
        self.assertEqual(_classify_title("Vintage Film Posters"), "NOT_WINE")
        self.assertEqual(_classify_title("Fine Chinese Ceramics"), "NOT_WINE")

    def test_is_wine_title_ground_truth(self):
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
                    "Shipping and Vintage Posters"]
        for title in not_wine:
            self.assertFalse(_is_wine_title(title), title)

    def test_validate_backfill_meta_ok(self):
        ok = {"sale_id": "18467", "sale_number": "5057", "saleroomcode": "PAR",
              "year": 2003, "month": 6}
        _validate_backfill_meta(ok)

    def test_validate_backfill_meta_raises_meta_invalid(self):
        with self.assertRaises(MetaInvalid):
            _validate_backfill_meta({"sale_id": "18467"})

    def test_discover_backfill_returns_refs_and_ambiguous(self):
        f = ChristiesFetcher()
        index = ('<sitemapindex><sitemap><loc>'
                 'https://www.christies.com/SiteMapPastSales1.xml'
                 '</loc></sitemap></sitemapindex>')
        wine_meta = ('{"sale_id":"12345","sale_number":"7187",'
                     '"sale_room_code":"LON","title":"Fine and Rare Wines",'
                     '"auction_status":{"start_date":"2020-06-01T00:00Z"}}')
        ambig_meta = ('{"sale_id":"99999","sale_number":"8888",'
                      '"sale_room_code":"NYC","title":"Rare Spirits of India",'
                      '"auction_status":{"start_date":"2019-03-01T00:00Z"}}')
        art_meta = ('{"sale_id":"18467","sale_number":"5057",'
                    '"sale_room_code":"PAR","title":"ART AFRICAIN",'
                    '"auction_status":{"start_date":"2003-06-12T00:00Z"}}')
        sales = ('<urlset>'
                 '<url><loc>https://www.christies.com/auction/'
                 'auction-5057-par/browse-lots</loc></url>'
                 '<url><loc>https://www.christies.com/auction/'
                 'auction-7187-lon/browse-lots</loc></url>'
                 '<url><loc>https://www.christies.com/auction/'
                 'auction-8888-nyc/browse-lots</loc></url>'
                 '</urlset>')

        class BackfillSession:
            request_count = 0

            def get(self, url):
                BackfillSession.request_count += 1
                if "LotFinder_Sitemap1" in url:
                    return FakeResponse(text=index)
                if "SiteMapPastSales" in url:
                    return FakeResponse(text=sales)
                if "auction-5057" in url:
                    return FakeResponse(text=art_meta)
                if "auction-8888" in url:
                    return FakeResponse(text=ambig_meta)
                return FakeResponse(text=wine_meta)

        refs, ambiguous = f.discover_backfill(BackfillSession())
        self.assertEqual([r.auction_id for r in refs], ["12345"])
        self.assertEqual(refs[0].title, "Fine and Rare Wines")
        self.assertEqual(len(ambiguous), 1)
        self.assertEqual(ambiguous[0]["sale_id"], "99999")
        self.assertIn("Spirits", ambiguous[0]["title"])

    @patch("ingest.fetchers.christies.time.sleep")
    def test_discover_backfill_delay_fires_per_url(self, mock_sleep):
        """Regression: delay must fire for every URL, not just wine hits."""
        f = ChristiesFetcher()
        index = ('<sitemapindex><sitemap><loc>'
                 'https://www.christies.com/SiteMapPastSales1.xml'
                 '</loc></sitemap></sitemapindex>')
        wine_meta = ('{"sale_id":"12345","sale_number":"7187",'
                     '"sale_room_code":"LON","title":"Fine and Rare Wines",'
                     '"auction_status":{"start_date":"2020-06-01T00:00Z"}}')
        art_meta = ('{"sale_id":"18467","sale_number":"5057",'
                    '"sale_room_code":"PAR","title":"ART AFRICAIN",'
                    '"auction_status":{"start_date":"2003-06-12T00:00Z"}}')
        sales = ('<urlset>'
                 '<url><loc>https://www.christies.com/auction/a1</loc></url>'
                 '<url><loc>https://www.christies.com/auction/a2</loc></url>'
                 '<url><loc>https://www.christies.com/auction/a3</loc></url>'
                 '</urlset>')

        class DelaySession:
            def get(self, url):
                if "LotFinder_Sitemap1" in url:
                    return FakeResponse(text=index)
                if "SiteMapPastSales" in url:
                    return FakeResponse(text=sales)
                if "a1" in url:
                    return FakeResponse(text=art_meta)
                if "a2" in url:
                    return FakeResponse(text=art_meta.replace(
                        "18467", "18468").replace("5057", "5058"))
                return FakeResponse(text=wine_meta)

        refs, _ = f.discover_backfill(DelaySession(), delay=0.5)
        self.assertEqual(len(refs), 1)
        self.assertEqual(mock_sleep.call_count, 3)
        for call in mock_sleep.call_args_list:
            self.assertEqual(call[0][0], 0.5)

    def test_discover_backfill_circuit_breaker(self):
        f = ChristiesFetcher()
        index = ('<sitemapindex><sitemap><loc>'
                 'https://www.christies.com/SiteMapPastSales1.xml'
                 '</loc></sitemap></sitemapindex>')
        sales = ('<urlset>'
                 + ''.join(f'<url><loc>https://www.christies.com/auction/'
                           f'auction-fail-{i}/browse-lots</loc></url>'
                           for i in range(5))
                 + '</urlset>')

        class FailSession:
            def get(self, url):
                if "LotFinder_Sitemap1" in url:
                    return FakeResponse(text=index)
                if "SiteMapPastSales" in url:
                    return FakeResponse(text=sales)
                return FakeResponse(text="", status_code=500)

        with self.assertRaises(RuntimeError):
            f.discover_backfill(FailSession(), max_fail=3)

    def test_discover_backfill_permanent_404_no_breaker(self):
        """Permanent 404s should not count toward the circuit breaker."""
        f = ChristiesFetcher()
        index = ('<sitemapindex><sitemap><loc>'
                 'https://www.christies.com/SiteMapPastSales1.xml'
                 '</loc></sitemap></sitemapindex>')
        wine_meta = ('{"sale_id":"12345","sale_number":"7187",'
                     '"sale_room_code":"LON","title":"Fine and Rare Wines",'
                     '"auction_status":{"start_date":"2020-06-01T00:00Z"}}')
        urls = ''.join(
            f'<url><loc>https://www.christies.com/auction/stale-{i}'
            f'/browse-lots</loc></url>' for i in range(5))
        urls += ('<url><loc>https://www.christies.com/auction/good'
                 '/browse-lots</loc></url>')
        sales = f'<urlset>{urls}</urlset>'

        class MixedSession:
            def get(self, url):
                if "LotFinder_Sitemap1" in url:
                    return FakeResponse(text=index)
                if "SiteMapPastSales" in url:
                    return FakeResponse(text=sales)
                if "stale" in url:
                    return FakeResponse(text="", status_code=404)
                return FakeResponse(text=wine_meta)

        refs, _ = f.discover_backfill(MixedSession(), max_fail=3)
        self.assertEqual(len(refs), 1)

    def test_get_retry_handles_retryable_errors(self):
        from ingest.fetchers.christies import _get_retry

        class ErrorSession:
            attempt = 0

            def get(self, url):  # pylint: disable=unused-argument
                ErrorSession.attempt += 1
                if ErrorSession.attempt < 3:
                    return FakeResponse(text="", status_code=429)
                return FakeResponse(text="ok content")

        result = _get_retry(ErrorSession(), "http://example.com",
                            max_retries=3)
        self.assertEqual(result, "ok content")

    def test_get_retry_returns_permanent_skip_on_404(self):
        from ingest.fetchers.christies import _get_retry

        class NotFoundSession:
            def get(self, url):  # pylint: disable=unused-argument
                return FakeResponse(text="", status_code=404)

        result = _get_retry(NotFoundSession(), "http://example.com")
        self.assertIs(result, PERMANENT_SKIP)


if __name__ == "__main__":
    unittest.main()
