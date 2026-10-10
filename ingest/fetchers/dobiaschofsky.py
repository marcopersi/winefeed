"""Fetcher for Dobiaschofsky (dobiaschofsky.com) wine results.

The wine page (``/d346.html``) lists the latest sold lots directly, each with
the hammer ("Zuschlag: CHF …"), the wine name and the auction reference.

- discover: return the single wine page as one auction ref.
- fetch: scrape the lots (``<li>`` cards) for name, hammer, lot number and
  auction reference.
"""
import re

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
            data={"auction": {"id": ref.auction_id, "name": None,
                              "date": None},
                  "lots": self._extract_lots(html)},
        )

    @staticmethod
    def _extract_lots(html):
        soup = BeautifulSoup(html, "html.parser")
        lots = []
        for form in soup.select("form[action*='d346-']"):
            action = form.get("action") or ""
            h3 = form.select_one("h3")
            description = form.select_one("p")
            zuschlag = form.select_one("div.gridtextheight2Highlights")
            lots.append({
                "lot_nr": _lot_id(action),
                "name": h3.get_text(strip=True) if h3 else None,
                "vintage": _year(action),
                "estimate_chf": None,
                "hammer_chf": _swiss_number(
                    zuschlag.get_text(strip=True) if zuschlag else None),
                "description": (description.get_text(strip=True)
                                if description else None),
            })
        return lots


def _lot_id(action):
    match = re.search(r"-(\d+)-", action)
    return match.group(1) if match else None


def _year(action):
    match = re.search(r"-(19|20)\d{2}", action)
    return match.group(0)[1:] if match else None


def _swiss_number(text):
    if not text:
        return None
    digits = re.sub(r"[^\d.]", "", text.replace("'", ""))
    return float(digits) if digits else None
