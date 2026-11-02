import unittest

from ingest.fetchers.winebarrel import WinebarrelFetcher

LIST_PAGE_1 = """
<div id="auctionItem1" data-position="1" data-auctionid="5372">
    <a href="/de/weinauktionen/auktionsarchiv/auction/5372">Château Mouton Rothschild 1986</a>
</div>
<div id="auctionItem2" data-position="2" data-auctionid="5371">
    <a href="/de/weinauktionen/auktionsarchiv/auction/5371">Something Else</a>
</div>
"""

LOT_PAGE = """
<title>Nit de Nin Mas d en Cacador 2018</title>
<strong>Land:</strong> Spanien <br />
<strong>Region:</strong> Cataluña / Priorat <br />
<strong>Region:</strong> Cataluña <br />
<strong>Weingut:</strong> <a href="/de/weinauktionen/auktionsarchiv/poi/1667-celler-familia-nin-ortiz">Celler Familia Nin Ortiz</a>
<br />
<strong>Flaschengrösse:</strong> 0.75l (Normalflasche) <br />
<strong>Anzahl Flaschen:</strong> 6 <br />
<strong>Auktions Nummer:</strong> 04183 <br />
<strong>Startpreis:</strong> CHF 1.00 (Inkl. MwSt.) <br />
<strong>Auktion beendet um:</strong> 2024-03-02 09:07:07 <br />
Zuschlagspreis (Inkl. MwSt.)<br />
<span id="maxbid">360.00</span>
"""

UNSOLD_LOT_PAGE = """
<title>Some Unsold Wine 2010</title>
<strong>Weingut:</strong> <a href="#">Some Producer</a>
<strong>Anzahl Flaschen:</strong> 1 <br />
<strong>Startpreis:</strong> CHF 50.00 (Inkl. MwSt.) <br />
"""


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.requests = []

    def get(self, url):
        self.requests.append(url)
        for key, text in self.pages.items():
            if key in url:
                return FakeResponse(text)
        return FakeResponse("")


class TestWinebarrel(unittest.TestCase):
    def test_discover_paginates_until_empty_page(self):
        f = WinebarrelFetcher()
        session = FakeSession({"start=0": LIST_PAGE_1, "start=20": ""})
        refs = f.discover(session)
        self.assertEqual([r.auction_id for r in refs], ["5372", "5371"])
        self.assertEqual(
            refs[0].url,
            "https://www.winebarrel.ch/de/weinauktionen/auktionsarchiv"
            "/auction/5372")

    def test_fetch_extracts_lot_fields(self):
        """Confirmed real case (auction 4183): the Region label appears
        twice (specific then broad) -- the first, more specific value
        wins. Weingut's value sits inside a nested <a> tag, not plain
        text after </strong>, so it needs its own pattern."""
        f = WinebarrelFetcher()
        session = FakeSession({"auction/4183": LOT_PAGE})
        from ingest.models import AuctionRef
        ref = AuctionRef("winebarrel", "4183",
                         url="https://www.winebarrel.ch/de/weinauktionen"
                             "/auktionsarchiv/auction/4183")
        result = f.fetch(session, ref)
        lot = result.data["lots"][0]
        self.assertEqual(lot["wine"], "Nit de Nin Mas d en Cacador 2018")
        self.assertEqual(lot["producer"], "Celler Familia Nin Ortiz")
        self.assertEqual(lot["region"], "Cataluña / Priorat")
        self.assertEqual(lot["quantity"], "6")
        self.assertEqual(lot["bottle_size_dl"], 7.5)
        self.assertEqual(lot["hammer_price"], 360.0)
        self.assertEqual(lot["sold"], 1)
        self.assertEqual(lot["auction_end"], "2024-03-02")

    def test_fetch_unsold_lot_has_no_hammer_price(self):
        f = WinebarrelFetcher()
        session = FakeSession({"auction/1": UNSOLD_LOT_PAGE})
        from ingest.models import AuctionRef
        ref = AuctionRef("winebarrel", "1",
                         url="https://www.winebarrel.ch/de/weinauktionen"
                             "/auktionsarchiv/auction/1")
        result = f.fetch(session, ref)
        lot = result.data["lots"][0]
        self.assertIsNone(lot["hammer_price"])
        self.assertEqual(lot["sold"], 0)


if __name__ == "__main__":
    unittest.main()
