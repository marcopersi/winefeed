"""Fetcher for Koppe & Partner (weinauktion.de) auction results.

- discover: parse ``/de/auktionen`` for auction ids.
- fetch: scrape the server-rendered lots from ``/de/auktionen/{id}?page={n}``.
"""
import re

from bs4 import BeautifulSoup

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.weinauktion.de"

_YEAR = re.compile(r"\b(19|20)\d{2}\b")


def _to_float(text):
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text)
    return float(digits) if digits else None


class KoppeFetcher:
    provider = "koppe"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def discover(self, session):
        html = session.get(f"{self.base_url}/de/auktionen").text
        soup = BeautifulSoup(html, "html.parser")
        refs = []
        seen = set()
        for a in soup.select('a[href^="/de/auktionen/"]'):
            match = re.match(r"/de/auktionen/(\d+)$", a.get("href", ""))
            if not match:
                continue
            # Only past auctions expose results; live ones say "zur Auktion".
            if "Ergebnisse ansehen" not in a.get_text():
                continue
            aid = match.group(1)
            if aid in seen:
                continue
            seen.add(aid)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=aid,
                url=f"{self.base_url}/de/auktionen/{aid}",
                title=f"Koppe {aid}",
            ))
        return refs

    def fetch(self, session, ref):
        lots = []
        page = 1
        while True:
            url = ref.url if page == 1 else f"{ref.url}?page={page}"
            html = session.get(url).text
            soup = BeautifulSoup(html, "html.parser")
            page_lots = self._parse_lots(soup)
            if not page_lots:
                break
            lots.extend(page_lots)
            if not self._has_next(soup, page):
                break
            page += 1
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"provider": self.provider, "auction_id": ref.auction_id,
                  "lots": lots},
        )

    @staticmethod
    def _has_next(soup, page):
        return soup.select_one(f'a[href$="?page={page + 1}"]') is not None

    def _parse_lots(self, soup):
        lots = []
        for name_el in soup.select(".lot-card-artikel-name"):
            card = name_el.find_parent(class_="card")
            name = name_el.get_text(" ", strip=True)
            vintage_match = _YEAR.search(name)
            color_img = card.select_one('img[title^="Weinfarbe"]')
            lots.append({
                "name": name,
                "vintage": vintage_match.group(0) if vintage_match else None,
                "region": _text(card, ".ursprung"),
                "color": color_img["title"].replace("Weinfarbe", "").strip()
                if color_img else None,
                "bottle_size": _text(card, ".size"),
                "format": [b.get_text(" ", strip=True).lstrip("| ").strip()
                           for b in card.select(".bundle")],
                "hammer_price": _to_float(_text(card, ".all-bids .bold")),
                "hammer_price_raw": _text(card, ".all-bids .bold"),
                "estimate": _text(card, ".schaetzung"),
            })
        return lots


def _text(card, selector):
    el = card.select_one(selector)
    return el.get_text(strip=True) if el else None
