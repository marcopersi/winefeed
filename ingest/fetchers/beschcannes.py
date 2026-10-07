"""Fetcher for Besch Cannes Auction (cannesauction.com) results.

- discover: parse ``/past-auctions-results-lots-catalogues`` for auction links
  (``/auctions/{id}-{slug}``).
- fetch: load the auction page and scrape the ``.shop-item`` cards: lot number
  (``title-product``), hammer (``.result`` = "Sold X EUR"), estimate
  (``shop-item-price``) and the lot detail URL (``/en-lots/{id}``).
"""
import re

from bs4 import BeautifulSoup

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.cannesauction.com"


class BeschCannesFetcher:
    provider = "besch-cannes"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def discover(self, session):
        html = session.get(
            f"{self.base_url}/past-auctions-results-lots-catalogues").text
        refs = []
        seen = set()
        for match in re.finditer(r'href="(/auctions/(\d+)-[^"]+)"', html):
            aid = match.group(2)
            if aid in seen:
                continue
            seen.add(aid)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=aid,
                url=self.base_url + match.group(1),
            ))
        return refs

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
        for item in soup.select(".shop-item"):
            result = item.select_one(".result")
            title = item.select_one(".title-product")
            estimate = item.select_one(".shop-item-price")
            link = item.select_one("a.shop-item-image")
            lots.append({
                "lot_no": title.get_text(strip=True) if title else None,
                "hammer": result.get_text(strip=True) if result else None,
                "estimate": estimate.get_text(strip=True) if estimate else None,
                "url": link.get("href") if link else None,
            })
        return lots
