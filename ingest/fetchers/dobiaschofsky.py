"""Fetcher for Dobiaschofsky (dobiaschofsky.com) wine results.

The wine page (``/d346.html``) lists the latest sold lots directly, each with
the hammer ("Zuschlag: CHF …"), the wine name and the auction reference.

- discover: return the single wine page as one auction ref.
- fetch: scrape the lots (``<li>`` cards) for name, hammer, lot number and
  auction reference.
"""
from bs4 import BeautifulSoup

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.dobiaschofsky.com"
WINE_PAGE = "/d346.html"


class DobiaschofskyFetcher:
    provider = "dobiaschofsky"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def discover(self, session):  # pylint: disable=unused-argument
        return [AuctionRef(
            provider=self.provider,
            auction_id="wein",
            url=self.base_url + WINE_PAGE,
        )]

    def fetch(self, session, ref):
        html = session.get(ref.url).text
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"provider": self.provider,
                  "auction_id": ref.auction_id,
                  "lots": self._extract_lots(html)},
        )

    @staticmethod
    def _extract_lots(html):
        soup = BeautifulSoup(html, "html.parser")
        lots = []
        for form in soup.select("form[action*='d346-']"):
            h3 = form.select_one("h3")
            zuschlag = form.select_one('span[style*="color:#004e6c"]')
            auction_ref = form.select_one('span[style*="font-size:11px"]')
            lots.append({
                "name": h3.get_text(strip=True) if h3 else None,
                "hammer": zuschlag.get_text(strip=True) if zuschlag else None,
                "auction": auction_ref.get_text(strip=True)
                if auction_ref else None,
                "url": form.get("action"),
            })
        return lots
