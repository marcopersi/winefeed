import unittest

from ingest.fetchers.dorotheum import DorotheumFetcher

OVERVIEW_HTML = (
    '<a href="/de/a/127195/">x</a> <a href="/de/a/125503/">y</a>'
    '<a href="/de/a/127195/">dup</a>')

LOT_PAGE = (
    'var hasResult = true; var lots = {"9515777":{"uid":9515777,'
    '"titel":"Château Mouton Rothschild","postennummer":"139-131145/0001",'
    '"preisFloat":400,"preis1":"EUR 400,-","preis2":"EUR 800,-",'
    '"preis3":"EUR 360,-"}};')


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


class TestDorotheum(unittest.TestCase):
    def test_discover_dedupes_auction_ids(self):
        f = DorotheumFetcher()
        refs = f.discover(FakeSession(
            {"auktionsergebnisse": OVERVIEW_HTML}))
        self.assertEqual([r.auction_id for r in refs], ["127195", "125503"])

    def test_fetch_extracts_lots(self):
        f = DorotheumFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("dorotheum", "127195",
                         url="https://www.dorotheum.com/de/a/127195/")
        result = f.fetch(FakeSession({"/de/a/127195/": LOT_PAGE}), ref)
        self.assertEqual(result.data["auction"]["id"], "127195")
        lots = result.data["lots"]
        self.assertEqual(len(lots), 1)
        lot = lots[0]
        self.assertEqual(lot["name"], "Château Mouton Rothschild")
        self.assertEqual(lot["lot_nr"], "139-131145/0001")
        self.assertEqual(lot["realized_price"], 400)
        self.assertEqual(lot["estimate"], 800)
        self.assertEqual(lot["currency"], "EUR")
        self.assertEqual(lot["sold"], 1)

    def test_parse_price_european_format(self):
        from ingest.fetchers.dorotheum import _parse_price
        self.assertEqual(_parse_price("EUR 800,-"), 800.0)
        self.assertEqual(_parse_price("EUR 1.500,-"), 1500.0)
        self.assertEqual(_parse_price("EUR 12.345,67"), 12345.67)
        self.assertIsNone(_parse_price(""))

    def test_parse_price_range_takes_low_end(self):
        """Confirmed real case: an unsold lot's estimate can be a range
        instead of one value -- broke CI (run 41257477575, 2026-11-01)
        with "could not convert string to float: '8000.10000.'"."""
        from ingest.fetchers.dorotheum import _parse_price
        self.assertEqual(
            _parse_price("EUR 8.000,- bis EUR 10.000,-"), 8000.0)


if __name__ == "__main__":
    unittest.main()
