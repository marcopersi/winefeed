import unittest

from ingest.fetchers.langtons import LangtonsFetcher

CLOSED_HTML = """
<a href="Auction-ShowDetails?id=8212&amp;name=F27UR014&amp;title=04%20SUN%3a%20Unreserved">
<a href="Auction-ShowDetails?id=8211&amp;name=F27SY014&amp;title=Shiraz">
"""

LOT_HTML = """
<tbody class="auction-closed-row-tbody">
  <tr><td class="column-header wine-name-sm"><p>919 WINES Tempranillo</p></td></tr>
  <tr class="auction-closed-sm-data">
    <td class="column-header" data-label="Lot #"><span>1</span></td>
    <td class="column-header hidden-sm-down">
      <p class="wine-name">919 WINES Ella Semmler Tempranillo</p>
      <p class="wine-description">South Australia</p>
    </td>
    <td class="column-header" data-label="Classification"><span></span></td>
    <td class="column-header" data-label="Vintage"><span>2019</span></td>
    <td class="column-header" data-label="Notes"><span>Screwcap Closure</span></td>
    <td class="column-header" data-label="Quantity"><span>1</span></td>
    <td class="column-header" data-label="Winning bid per item"><span>$3.00</span></td>
  </tr>
</tbody>
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
        for key, text in self._pages.items():
            if key in url:
                return FakeResponse(text)
        return FakeResponse("")


class TestLangtons(unittest.TestCase):
    def test_discover_parses_closed_auctions(self):
        f = LangtonsFetcher()
        session = FakeSession({"Auction-ClosedAuction": CLOSED_HTML})
        refs = f.discover(session)
        self.assertEqual([r.auction_id for r in refs], ["8212", "8211"])
        self.assertEqual(refs[0].title, "04 SUN: Unreserved")

    def test_fetch_parses_lots(self):
        f = LangtonsFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("langtons", "8212",
                         url="https://x/Auction-ShowDetails?id=8212"
                             "&name=F27UR014&clearSearch=true&isAjax=true")
        session = FakeSession({"isAjax=true": LOT_HTML})
        result = f.fetch(session, ref)
        lot = result.data["lots"][0]
        self.assertEqual(lot["wine"], "919 WINES Ella Semmler Tempranillo")
        self.assertEqual(lot["region"], "South Australia")
        self.assertEqual(lot["vintage"], "2019")
        self.assertEqual(lot["winning_bid"], 3.0)


if __name__ == "__main__":
    unittest.main()
