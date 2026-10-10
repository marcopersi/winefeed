"""Fetcher for Besch Cannes Auction (cannesauction.com) results.

- discover: parse ``/past-auctions-results-lots-catalogues`` for auction links
  (``/auctions/{id}-{slug}``).
- fetch: load the auction page, scrape the ``.shop-item`` cards for the lot
  number, estimate and hammer, then load each lot's detail page
  (``/en-lots/{id}``) for the wine name, vintage and description.
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
        cards = self._extract_cards(html)
        lots = []
        for card in cards:
            lot = self._map_card(card)
            if card.get("url"):
                detail = session.get(self.base_url + card["url"]).text
                lot.update(self._parse_detail(detail))
            lots.append(lot)
        slug = re.search(r"/auctions/(\d+-[a-z0-9\-]+)", ref.url)
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"auction": {"id": ref.auction_id,
                              "slug": slug.group(1) if slug else None,
                              "date": None, "currency": "EUR",
                              "price_basis": "HAMMER"},
                  "lots": lots},
        )

    @staticmethod
    def _extract_cards(html):
        soup = BeautifulSoup(html, "html.parser")
        cards = []
        for item in soup.select(".shop-item"):
            result = item.select_one(".result")
            title = item.select_one(".title-product")
            estimate = item.select_one(".shop-item-price")
            link = item.select_one("a.shop-item-image")
            cards.append({
                "lot_no": title.get_text(strip=True) if title else None,
                "hammer": result.get_text(strip=True) if result else None,
                "estimate": estimate.get_text(strip=True)
                if estimate else None,
                "url": link.get("href") if link else None,
            })
        return cards

    @staticmethod
    def _map_card(card):
        return {
            "lot_no": _lot_no(card.get("lot_no")),
            "appellation": None,
            "vintage": None,
            "estimate": _estimate(card.get("estimate")),
            "adjuge": _hammer(card.get("hammer")),
            "description": None,
            "remarks": None,
        }

    @staticmethod
    def _parse_detail(html):
        soup = BeautifulSoup(html, "html.parser")
        text = None
        for p in soup.find_all("p"):
            candidate = p.get_text(" ", strip=True)
            if candidate and ("Année" in candidate
                              or "Appellation" in candidate
                              or "Bouteille" in candidate):
                text = candidate
                break
        if not text:
            return {}
        return {
            "appellation": _appellation(text),
            "vintage": _vintage(text),
            "description": text,
        }


def _lot_no(text):
    match = re.search(r"n°\s*(\d+)", text or "")
    return match.group(1) if match else None


def _estimate(text):
    match = re.search(r"([\d\s\.]+)\s*€\s*/\s*([\d\s\.]+)\s*€", text or "")
    if not match:
        return None
    return [_euro(match.group(1)), _euro(match.group(2))]


def _hammer(text):
    match = re.search(r"([\d\s\.]+)\s*€", text or "")
    return _euro(match.group(1)) if match else None


def _euro(text):
    digits = re.sub(r"[^\d.]", "", text or "")
    return float(digits) if digits else None


def _vintage(text):
    match = re.search(r"Année\s*:\s*(\d{4})", text or "")
    return match.group(1) if match else None


def _appellation(text):
    match = re.search(r'"([^"]+)"', text or "")
    return match.group(1) if match else None
