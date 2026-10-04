"""Fetcher for Langtons closed-auction results.

- discover: parse ``Auction-ClosedAuction`` for ``Auction-ShowDetails?id=…``
  entries (closed auctions).
- fetch: load ``Auction-ShowDetails?…&isAjax=true`` pages and scrape the
  ``auction-closed-row-tbody`` lot rows (incl. ``Winning bid per item``).
"""
import re
from urllib.parse import unquote

from bs4 import BeautifulSoup

from ..models import AuctionRef, FetchResult

BASE_URL = ("https://www.langtons.com.au/on/demandware.store/"
            "Sites-langtons-Site/en_AU")

SHOW_LINK = re.compile(
    r'Auction-ShowDetails\?id=(\d+)&(?:amp;)?name=([^&"]+)'
    r'&(?:amp;)?title=([^"&]+)')


def _money(text):
    if not text:
        return None
    digits = re.sub(r"[^\d.]", "", text)
    return float(digits) if digits else None


class LangtonsFetcher:
    provider = "langtons"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def discover(self, session):
        url = (f"{self.base_url}/Auction-ClosedAuction"
               f"?cgid=cat-auctions-auction-results-and-reports"
               f"&auctionStatus=Closed")
        html = session.get(url).text
        refs = []
        seen = set()
        for match in SHOW_LINK.finditer(html):
            aid, name, title = match.group(1), match.group(2), match.group(3)
            if aid in seen:
                continue
            seen.add(aid)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=aid,
                url=(f"{self.base_url}/Auction-ShowDetails?id={aid}"
                     f"&name={name}&clearSearch=true&isAjax=true"),
                title=unquote(title),
            ))
        return refs

    def fetch(self, session, ref):
        lots = []
        offset = 0
        while True:
            url = (f"{ref.url}&offset={offset}&searchTerm="
                   f"&totalcount=999999&currentItemsCount=2")
            page_lots = self._parse_lots(session.get(url).text)
            if not page_lots:
                break
            lots.extend(page_lots)
            if len(page_lots) < 20:
                break
            offset += 20
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"provider": self.provider,
                  "auction_id": ref.auction_id,
                  "title": ref.title,
                  "lots": lots},
        )

    @staticmethod
    def _parse_lots(html):
        soup = BeautifulSoup(html, "html.parser")
        lots = []
        for tbody in soup.select(".auction-closed-row-tbody"):
            name_el = tbody.select_one(".wine-name")
            desc_el = tbody.select_one(".wine-description")
            fields = {}
            for td in tbody.select("td[data-label]"):
                fields[td.get("data-label")] = td.get_text(strip=True)
            lots.append({
                "lot_no": fields.get("Lot #"),
                "wine": name_el.get_text(strip=True) if name_el else None,
                "region": desc_el.get_text(strip=True) if desc_el else None,
                "classification": fields.get("Classification"),
                "vintage": fields.get("Vintage"),
                "notes": fields.get("Notes"),
                "quantity": fields.get("Quantity"),
                "winning_bid": _money(fields.get("Winning bid per item")),
            })
        return lots
