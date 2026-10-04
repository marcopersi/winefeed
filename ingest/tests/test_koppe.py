import unittest

from ingest.fetchers.koppe import KoppeFetcher

LIST_HTML = """
<a href="/de/auktionen/13">zur Auktion</a>
<a href="/de/auktionen/12">Ergebnisse ansehen</a>
<a href="/de/auktionen/10">Ergebnisse ansehen</a>
"""

LOT_HTML = """
<div class="card">
  <div class="artikel p-2">
    <div class="artikel-name bold">
      <p class="lot-card-artikel-name">Chateau Haut-Brion<br>Chateau Haut-Brion 1998</p>
    </div>
    <div class="ursprung">Pessac-Leognan</div>
    <div class="settings pt-2">
      <img title="Weinfarbe Rot">
      <span class="size">6,0 l</span>
      <span class="bundle">1 Imperial </span>
    </div>
  </div>
  <div class="auktion-card-footer mt-auto">
    <div class="all-bids px-2 text-center">
      (1 Gebot) aktuell: <span class="bold">6.000,- EUR</span>
    </div>
    <div class="schaetzung text-center bold">6.000,- EUR - 12.000,- EUR</div>
  </div>
</div>
"""


class FakeResponse:
    def __init__(self, text):
        self.text = text
        self.content = b""

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, pages):
        self._pages = pages
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        return FakeResponse(self._pages.get(url, ""))


class TestKoppe(unittest.TestCase):
    def test_discover_ids(self):
        f = KoppeFetcher()
        refs = f.discover(FakeSession({
            "https://www.weinauktion.de/de/auktionen": LIST_HTML}))
        self.assertEqual([r.auction_id for r in refs], ["12", "10"])

    def test_fetch_parses_lots(self):
        f = KoppeFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("koppe", "10", url="https://www.weinauktion.de/de/auktionen/10")
        session = FakeSession({
            "https://www.weinauktion.de/de/auktionen/10": LOT_HTML,
        })
        result = f.fetch(session, ref)
        lots = result.data["lots"]
        self.assertEqual(len(lots), 1)
        lot = lots[0]
        self.assertEqual(lot["region"], "Pessac-Leognan")
        self.assertEqual(lot["vintage"], "1998")
        self.assertEqual(lot["bottle_size"], "6,0 l")
        self.assertEqual(lot["hammer_price"], 6000.0)
        self.assertEqual(lot["color"], "Rot")


if __name__ == "__main__":
    unittest.main()
